#!/usr/bin/env python
import sys
from typing import Any, Callable, TypeVar

import dotenv
from eth_typing import ChecksumAddress
from web3._utils.events import get_event_data
from web3.types import EventData, Wei
from xrpl.models import Memo, Response
from xrpl.utils import ripple_time_to_posix

from src import cli, encoder, flare_client, xrpl_client
from src.cli.types import (
    BridgeClaimWithdraw,
    BridgeCustom,
    BridgeDeposit,
    BridgeMint,
    BridgeRedeem,
    BridgeWithdraw,
    DebugCheckStatus,
    DebugMockCreateFund,
    DebugMockCustom,
    DebugMockPrint,
    DebugSimulation,
    NamespaceSerializer,
    PersonalAccountFaucet,
    PersonalAccountPrint,
)
from src.registry import registry
from src.settings import settings


def reserve_collateral(agent_address: ChecksumAddress, lots: int) -> Response:
    memo_data = encoder.reserve_collateral(agent_address, lots).hex()
    return xrpl_client.send_bridge_request_tx(memo_data)


def bridge_pp(resp: Response) -> EventData | None:
    print("sent instruction on underlying:", resp.result["hash"])
    print(f"https://testnet.xrpl.org/transactions/{resp.result['hash']}/detailed")
    print()
    bridged = flare_client.wait_until_bridged(resp)

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
    bridge_pp(resp)


def mint(args: BridgeMint) -> None:
    w3 = settings.w3

    resp = reserve_collateral(args.agent_address, args.lots)
    bridged = bridge_pp(resp)
    if bridged is None:
        print("failed to bridge")
        return
    bridged_tx_hash, bridged_tx_block = (
        bridged["transactionHash"].hex(),
        bridged["blockNumber"],
    )

    cr_event = registry.asset_manager_events.events["CollateralReserved"]
    cr_log = flare_client.get_event(cr_event, bridged_tx_block)
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

    block = flare_client.find_block_near_timestamp(
        ripple_time_to_posix(resp.result["tx_json"]["date"]) - 90
    )

    bridged = flare_client.wait_for_event(
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
    bridge_pp(resp)


def withdraw(args: BridgeWithdraw) -> None:
    memo_data = encoder.withdraw(args.amount).hex()
    resp = xrpl_client.send_bridge_request_tx(memo_data)
    bridge_pp(resp)


def claim_withdraw(args: BridgeClaimWithdraw) -> None:
    memo_data = encoder.claim_withdraw(1).hex()
    resp = xrpl_client.send_bridge_request_tx(memo_data)
    bridge_pp(resp)


def redeem(args: BridgeRedeem) -> None:
    memo_data = encoder.deposit(args.lots).hex()
    resp = xrpl_client.send_bridge_request_tx(memo_data)
    bridge_pp(resp)


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
    evnt_log = flare_client.get_event(evnt, block)
    data = get_event_data(w3.codec, evnt.abi, evnt_log)
    call_hash = data["args"]["callHash"].to_bytes(31)
    memo_data = encoder.custom(call_hash).hex()
    resp = xrpl_client.send_bridge_request_tx(memo_data)
    bridge_pp(resp)


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


def debug_mock_print(args: DebugMockPrint) -> int | None:
    w3 = settings.w3
    pk = settings.env.flr_private_key
    addr = w3.eth.account.from_key(pk).address

    print(
        w3.eth.contract(
            address=registry.concat_this.address,
            abi=registry.concat_this.abi,
        )
        .functions.concatAddr(args.seed, addr)
        .call()
    )


def mock_create_fund(args: DebugMockCreateFund) -> int | None:
    w3 = settings.w3
    pk = settings.env.flr_private_key
    addr = w3.eth.account.from_key(pk).address

    tx = (
        w3.eth.contract(
            address=registry.master_account_controller_dev_mock.address,
            abi=registry.master_account_controller_dev_mock.abi,
        )
        .functions.createFundPersonalAccount(args.seed)
        .build_transaction(
            {
                "from": addr,
                "nonce": w3.eth.get_transaction_count(addr),
                "gasPrice": Wei(round(w3.eth.gas_price * 1.5)),
                "value": args.value,
            }
        )
    )

    rtx = w3.eth.account.sign_transaction(tx, pk)
    tx_hash = w3.eth.send_raw_transaction(rtx.raw_transaction)
    rec = w3.eth.wait_for_transaction_receipt(tx_hash)
    print(f"0x{rec['transactionHash'].hex()}")


def personal_account_print(args: PersonalAccountPrint) -> int | None:
    w3 = settings.w3
    print(
        w3.eth.contract(
            address=registry.master_account_controller.address,
            abi=registry.master_account_controller.abi,
        )
        .functions.getPersonalAccount(args.xrpl_address_parsed)
        .call()
    )


def personal_account_faucet(args: PersonalAccountPrint) -> int | None:
    w3 = settings.w3

    account = (
        w3.eth.contract(
            address=registry.master_account_controller.address,
            abi=registry.master_account_controller.abi,
        )
        .functions.getPersonalAccount(args.xrpl_address_parsed)
        .call()
    )
    print("account is:", account)
    print("you can faucet here: https://faucet.flare.network/coston2")


def not_implemented(args: Any) -> int | None:
    print(args)
    print("error: not implemented")
    return 2


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
            "mock-print": (DebugMockPrint, debug_mock_print),
            "mock-create-fund": (DebugMockCreateFund, mock_create_fund),
            "mock-custom": (DebugMockCustom, mock_custom),
            "simulation": (DebugSimulation, simulation),
            "check-status": (DebugCheckStatus, check_status),
        },
        "personal-account": {
            "print": (PersonalAccountPrint, personal_account_print),
            "faucet": (PersonalAccountFaucet, personal_account_faucet),
        },
    }

    r = resolver.get(args.command, {}).get(args.subcommand)
    if r is None:
        exit(not_implemented(args))

    serializer, resolver_fn = r
    try:
        exit_code = resolver_fn(serializer.from_namespace(args))
        if exit_code is not None:
            exit(exit_code)
    except ValueError as e:
        print(f"error: {', '.join(map(str, e.args))}", file=sys.stderr)
        exit(2)


def main() -> None:
    dotenv.load_dotenv()
    return smart_accounts()


if __name__ == "__main__":
    main()
