#!/usr/bin/env python
import sys
import time
from collections.abc import Iterator, Sequence
from typing import Callable, TypeVar

import dotenv
from eth_typing import ChecksumAddress
from web3 import Web3
from web3._utils.events import get_event_data
from web3.types import EventData, LogReceipt, Wei
from xrpl.models import Memo, Response
from xrpl.utils import ripple_time_to_posix

from src import cli, encoder, xrpl_client
from src.cli.types import (
    BridgeClaimWithdraw,
    BridgeCustom,
    BridgeDeposit,
    BridgeMint,
    BridgeRedeem,
    BridgeWithdraw,
    DebugCheckStatus,
    DebugMockCustom,
    DebugSimulation,
    NamespaceSerializer,
)
from src.registry import Event, registry
from src.settings import settings


def scan_events(
    w3: Web3, events: Sequence[Event], block_range: tuple[int, int]
) -> Iterator[LogReceipt]:
    addresses = list({e.contract.address for e in events})
    signatures = {e.signature for e in events}

    start, end = block_range
    for block in range(start, end, 30):
        latest = w3.eth.block_number
        if block > latest:
            break

        logs = w3.eth.get_logs(
            {
                "address": addresses,
                "fromBlock": block,
                "toBlock": min(block + 30 - 1, latest),
            }
        )

        for log in logs:
            if log["topics"][0].hex() in signatures:
                yield log


def get_flr_block_near_ts(w3: Web3, timestamp: int) -> int:
    b = w3.eth.get_block("latest")
    assert "timestamp" in b and "number" in b
    assert timestamp < b["timestamp"]

    p_sample = w3.eth.get_block(b["number"] - 1_000_000)
    assert "timestamp" in p_sample and "number" in p_sample

    production_per_s = (b["number"] - p_sample["number"]) / (
        b["timestamp"] - p_sample["timestamp"]
    )

    a = w3.eth.get_block(
        b["number"] - int((b["timestamp"] - timestamp) * production_per_s) * 2
    )
    assert "timestamp" in a and "number" in a
    assert timestamp > a["timestamp"]

    while True:
        c_block = (b["number"] + a["number"]) // 2
        c = w3.eth.get_block(c_block)
        assert "timestamp" in c and "number" in c

        if abs(c["timestamp"] - timestamp) < 10:
            return c["number"]

        if c["timestamp"] > timestamp:
            (a, b) = (a, c)
        else:
            (a, b) = (c, b)


def wait_for_event(
    w3: Web3,
    event: Event,
    block_range: tuple[int, int],
    filter_fn: Callable[[EventData], bool],
    message: str | None = None,
) -> EventData | None:
    while True:
        if message is not None:
            print(message)

        for e in scan_events(w3, (event,), block_range):
            data = get_event_data(w3.codec, event.abi, e)
            if filter_fn(data):
                return data

        if w3.eth.block_number > block_range[1]:
            break

        time.sleep(10)


def wait_to_bridge(w3, r: Response) -> EventData | None:
    block = get_flr_block_near_ts(
        w3, ripple_time_to_posix(r.result["tx_json"]["date"]) - 90
    )

    event = registry.master_account_controller.events["InstructionExecuted"]

    return wait_for_event(
        w3,
        event,
        (block, block + 4 * 90),
        lambda x: x["args"]["transactionId"].hex() == r.result["hash"].lower(),
        "waiting to bridge",
    )


def reserve_collateral(agent_address: ChecksumAddress, lots: int) -> Response:
    memo_data = encoder.reserve_collateral(agent_address, lots).hex()
    return xrpl_client.send_bridge_request_tx(memo_data)


def bridge_pp(w3, resp: Response) -> EventData | None:
    print("sent instruction on underlying:", resp.result["hash"])
    print(f"https://testnet.xrpl.org/transactions/{resp.result['hash']}/detailed")
    print()
    bridged = wait_to_bridge(w3, resp)

    if bridged is None:
        print("failed to bridge")
        return

    bridged_tx_hash = bridged["transactionHash"].hex()
    print(f"BRIDGED FOR {bridged['args']['personalAccount']}")
    print(f"successfully bridged in tx 0x{bridged_tx_hash}")
    print(f"https://coston2-explorer.flare.network/tx/0x{bridged_tx_hash}?tab=logs")
    print()

    return bridged


def check_status(args: DebugCheckStatus) -> None:
    resp = xrpl_client.get_tx(args.xrpl_hash.hex())
    bridge_pp(settings.w3, resp)


def mint(args: BridgeMint) -> None:
    w3 = settings.w3

    resp = reserve_collateral(args.agent_address, args.lots)
    bridged = bridge_pp(w3, resp)
    if bridged is None:
        print("failed to bridge")
        return
    bridged_tx_hash, bridged_tx_block = (
        bridged["transactionHash"].hex(),
        bridged["blockNumber"],
    )

    cr_event = registry.asset_manager_events.events["CollateralReserved"]
    cr_log = next(
        scan_events(w3, (cr_event,), (bridged_tx_block, bridged_tx_block + 1))
    )
    data = get_event_data(w3.codec, cr_event.abi, cr_log)

    _args = data["args"]
    amount = str(_args["valueUBA"] + _args["feeUBA"])
    destination = _args["paymentAddress"]
    memo = _args["paymentReference"].hex()
    last_ledger_sequence = _args["lastUnderlyingBlock"]
    collateral_reservation_id = _args["collateralReservationId"]

    input(
        "successful collateral resevation, continue to 2nd part of mint... press enter"
    )
    resp = xrpl_client.send_tx(amount, destination, memo, last_ledger_sequence)
    print("sent underlying assets in", resp.result["hash"])
    print(f"https://testnet.xrpl.org/transactions/{resp.result['hash']}/detailed")

    me_event = registry.asset_manager_events.events["MintingExecuted"]

    block = get_flr_block_near_ts(
        w3, ripple_time_to_posix(resp.result["tx_json"]["date"]) - 90
    )

    bridged = wait_for_event(
        w3,
        me_event,
        (block, block + 90 * 4),
        lambda x: x["args"]["collateralReservationId"] == collateral_reservation_id,
        "waiting for mint execution",
    )

    if bridged is None:
        print("failed to bridge")
        return

    bridged_tx_hash, bridged_tx_block = (
        bridged["transactionHash"].hex(),
        bridged["blockNumber"],
    )
    print("successfully minted in tx", "0x" + bridged_tx_hash)
    print(f"https://coston2-explorer.flare.network/tx/{bridged_tx_hash}?tab=logs")
    print()


def memo(memo_data: str) -> Memo:
    return Memo(memo_data=memo_data)


def deposit(args: BridgeDeposit) -> None:
    memo_data = encoder.deposit(args.amount).hex()
    resp = xrpl_client.send_bridge_request_tx(memo_data)
    bridge_pp(settings.w3, resp)


def withdraw(args: BridgeWithdraw) -> None:
    memo_data = encoder.withdraw(args.amount).hex()
    resp = xrpl_client.send_bridge_request_tx(memo_data)
    bridge_pp(settings.w3, resp)


def claim_withdraw(args: BridgeClaimWithdraw) -> None:
    memo_data = encoder.claim_withdraw(args.reward_epoch).hex()
    resp = xrpl_client.send_bridge_request_tx(memo_data)
    bridge_pp(settings.w3, resp)


def redeem(args: BridgeRedeem) -> None:
    memo_data = encoder.deposit(args.lots).hex()
    resp = xrpl_client.send_bridge_request_tx(memo_data)
    bridge_pp(settings.w3, resp)


def simulation(args: DebugSimulation):
    mint(
        BridgeMint(agent_address=args.agent_address, lots=args.mint),
    )
    print("minted fassets, check here:")
    print(
        "https://coston2-explorer.flare.network/address/0x0b6A3645c240605887a5532109323A3E12273dc7?tab=read_proxy"
    )
    print()
    input("continue to deposit... press enter")
    deposit(BridgeDeposit(amount=args.deposit))
    print("deposited into vault, check here:")
    print(
        "https://coston2-explorer.flare.network/address/0x912DbF2173bD48ec0848357a128652D4c0fc33EB?tab=read_contract"
    )
    print()
    input("continue to withdraw... press enter")
    withdraw(BridgeWithdraw(amount=args.deposit))
    claim_withdraw(BridgeClaimWithdraw(reward_epoch=1))
    print("withdrawn from vault, check here:")
    print(
        "https://coston2-explorer.flare.network/address/0x912DbF2173bD48ec0848357a128652D4c0fc33EB?tab=read_contract"
    )
    print()
    input("continue to redeem... press enter")
    redeem(BridgeRedeem(lots=args.mint))


def custom(args: BridgeCustom) -> None:
    w3 = settings.w3
    pk = settings.env.flr_private_key
    assert pk
    addr = w3.eth.account.from_key(pk).address
    tx = (
        w3.eth.contract(
            address=registry.master_account_controller.address,
            abi=registry.master_account_controller.abi,
        )
        .functions.registerCustomInstruction(
            [(a.address, a.value, a.data) for a in args.serialized]
        )
        .build_transaction(
            {
                "from": addr,
                "nonce": w3.eth.get_transaction_count(addr),
                "gasPrice": Wei(round(w3.eth.gas_price * 1.5)),
            }
        )
    )

    rtx = w3.eth.account.sign_transaction(tx, pk)
    tx_hash = w3.eth.send_raw_transaction(rtx.raw_transaction)
    rec = w3.eth.wait_for_transaction_receipt(tx_hash)
    block = rec["blockNumber"]
    evnt = registry.master_account_controller.events["CustomInstructionRegistered"]
    evnt_log = next(scan_events(w3, (evnt,), (block, block + 1)))
    data = get_event_data(w3.codec, evnt.abi, evnt_log)
    call_hash = data["args"]["callHash"].to_bytes(31)
    memo_data = encoder.custom(call_hash).hex()
    resp = xrpl_client.send_bridge_request_tx(memo_data)
    bridge_pp(w3, resp)


def mock_custom(args: DebugMockCustom) -> int | None:
    w3 = settings.w3
    pk = settings.env.flr_private_key
    addr = w3.eth.account.from_key(pk).address

    tx = (
        w3.eth.contract(
            address=registry.master_account_controller_dev_mock.address,
            abi=registry.master_account_controller_dev_mock.abi,
        )
        .functions.executeCustomInstructionDevelopment(
            args.seed, [(a.address, a.value, a.data) for a in args.serialized]
        )
        .build_transaction(
            {
                "from": addr,
                "nonce": w3.eth.get_transaction_count(addr),
                "gasPrice": Wei(round(w3.eth.gas_price * 1.5)),
            }
        )
    )

    rtx = w3.eth.account.sign_transaction(tx, pk)
    tx_hash = w3.eth.send_raw_transaction(rtx.raw_transaction)
    rec = w3.eth.wait_for_transaction_receipt(tx_hash)
    print(f"0x{rec['transactionHash'].hex()}")


T = TypeVar("T", bound=NamespaceSerializer)
Resolver = dict[str, tuple[type[T], Callable[[T], int | None]]]


def smart_accounts() -> None:
    args = cli.get_parser().parse_args()

    resolver: dict[str, Resolver] = {
        "bridge": {
            "deposit": (BridgeDeposit, deposit),
            "withdraw": (BridgeWithdraw, withdraw),
            "redeem": (BridgeRedeem, redeem),
            "mint": (BridgeMint, mint),
            "claim-withdraw": (BridgeClaimWithdraw, claim_withdraw),
            "custom": (BridgeCustom, custom),
        },
        "debug": {
            "mock-custom": (DebugMockCustom, mock_custom),
            "simulation": (DebugSimulation, simulation),
            "check-status": (DebugCheckStatus, check_status),
        },
    }

    r = resolver.get(args.command, {}).get(args.subcommand)
    if r is None:
        print("error: not implemented")
        exit(2)

    serializer, resolver_fn = r
    try:
        exit_code = resolver_fn(serializer.from_namespace(args))
        if exit_code is not None:
            exit(exit_code)
    except ValueError as e:
        print(f"error: {', '.join(e.args)}", file=sys.stderr)
        exit(2)


def main() -> None:
    dotenv.load_dotenv()
    return smart_accounts()


if __name__ == "__main__":
    main()
