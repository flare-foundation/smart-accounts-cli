#!/usr/bin/env python

import json
import os
import time
from collections.abc import Iterator, Sequence
from typing import Callable, Self

import attrs
import dotenv
from attrs import field, frozen
from eth_typing import ABI, ABIEvent, ABIFunction, ChecksumAddress
from eth_utils.address import to_checksum_address
from web3 import Web3
from web3._utils.events import get_event_data
from web3.middleware.proof_of_authority import ExtraDataToPOAMiddleware
from web3.types import EventData, LogReceipt, Wei
from xrpl.account import get_next_valid_seq_number
from xrpl.clients import JsonRpcClient
from xrpl.ledger import get_latest_validated_ledger_sequence
from xrpl.models import Memo, Payment, Response, Tx
from xrpl.transaction import sign, submit_and_wait
from xrpl.utils import ripple_time_to_posix
from xrpl.wallet import Wallet

from src import cli, encoder
from src.cli.types import (
    BridgeCustom,
    BridgeDeposit,
    BridgeMint,
    BridgeRedeem,
    BridgeWithdraw,
    NamespaceSerializer,
)


@attrs.frozen(kw_only=True)
class ParsedEnv:
    xrp_seed: str
    flr_private_key: str
    flr_rpc_url: str
    xrp_rpc_url: str

    @classmethod
    def from_env(cls) -> Self:
        # TODO:(janezicmatej) add validation and nice error
        xrp_seed = os.environ["XRP_SEED"]
        flr_private_key = os.environ["FLR_PRIVATE_KEY"]
        flr_rpc_url = os.environ["FLR_RPC_URL"]
        xrp_rpc_url = os.environ["XRP_RPC_URL"]

        return cls(
            xrp_seed=xrp_seed,
            flr_private_key=flr_private_key,
            flr_rpc_url=flr_rpc_url,
            xrp_rpc_url=xrp_rpc_url,
        )


@attrs.frozen(kw_only=True)
class Globals:
    w3: Web3
    xrp: JsonRpcClient
    env: ParsedEnv


def abi_from_file_location(file_location: str):
    return json.load(open(file_location))["abi"]


def event_signature(event_abi: ABIEvent) -> str:
    assert "inputs" in event_abi
    params = ""
    for index, input in enumerate(event_abi["inputs"]):
        if index > 0:
            params += ","

        if input["type"] == "tuple[]":
            params += "("
            assert "components" in input
            for index2, tuple_component in enumerate(input["components"]):
                if index2 > 0:
                    params += ","

                params += tuple_component["type"]

            params += ")[]"

        elif input["type"] == "tuple":
            params += "("
            assert "components" in input
            for index2, tuple_component in enumerate(input["components"]):
                if index2 > 0:
                    params += ","

                params += tuple_component["type"]

            params += ")"

        else:
            params += input["type"]

    return Web3.keccak(text=event_abi["name"] + "(" + params + ")").hex()


def function_signature(function_name: str) -> str:
    return Web3.keccak(text=function_name).hex()[:8]


@frozen
class Event:
    name: str
    abi: ABIEvent
    contract: "Contract"
    signature: str = field(init=False)

    def __attrs_post_init__(self):
        object.__setattr__(self, "signature", event_signature(self.abi))


@frozen
class Function:
    name: str
    abi: ABIFunction
    contract: "Contract"
    signature: str = field(init=False)

    def to_full_name(self):
        assert "inputs" in self.abi
        inputs = [i["type"] for i in self.abi["inputs"]]
        return f"{self.name}({','.join(inputs)})"

    def __attrs_post_init__(self):
        object.__setattr__(self, "signature", function_signature(self.to_full_name()))


@frozen
class Contract:
    name: str
    address: ChecksumAddress
    abi: ABI = field(converter=abi_from_file_location)
    events: dict[str, Event] = field(init=False)
    functions: dict[str, Function] = field(init=False)

    def __attrs_post_init__(self):
        events = {}
        functions = {}
        for entry in self.abi:
            assert "type" in entry
            if entry["type"] == "event":
                assert "name" in entry
                events[entry["name"]] = Event(entry["name"], entry, self)
            elif entry["type"] == "function":
                assert "name" in entry
                functions[entry["name"]] = Function(entry["name"], entry, self)
        object.__setattr__(self, "events", events)
        object.__setattr__(self, "functions", functions)


class REG:
    MASTER_ACCOUNT_CONTROLLER = Contract(
        name="MasterAccountController",
        address=to_checksum_address("0xFE127Fd68FB4F37ECFB0135FbB42954c5A5fCfaA"),
        abi="./abis/MasterAccountController.json",
    )

    ASSET_MANAGER_EVENTS = Contract(
        name="AssetManagerFXRP",
        address=to_checksum_address("0xc1Ca88b937d0b528842F95d5731ffB586f4fbDFA"),
        abi="./abis/IAssetManagerEvents.json",
    )


def send_xpr_tx(
    xrp: JsonRpcClient,
    amount: str,
    destination: str,
    memos: list[Memo] | None,
    last_ledger_sequence: int | None,
) -> Response:
    client = JsonRpcClient(os.getenv("XRP_RPC_URL", ""))

    seed = os.getenv("XRP_SEED")
    assert seed

    if last_ledger_sequence is None:
        last_ledger_sequence = get_latest_validated_ledger_sequence(client) + 20

    wallet_from_seed = Wallet.from_seed(seed)

    payment_tx = Payment(
        account=wallet_from_seed.address,
        amount=amount,
        destination=destination,
        memos=memos,
        last_ledger_sequence=last_ledger_sequence,
        sequence=get_next_valid_seq_number(wallet_from_seed.address, client),
        fee="10",
    )

    payment_response = submit_and_wait(sign(payment_tx, wallet_from_seed), client)
    return get_xrp_tx(xrp, payment_response.result["hash"])


def bridge_tx(xrp: JsonRpcClient, memos: list[Memo] | None) -> Response:
    op_addr = os.getenv("OPERATOR_ADDRESS")
    assert op_addr
    return send_xpr_tx(xrp, "1", op_addr, memos, None)


def get_w3_client(rpc_url: str) -> Web3:
    w3 = Web3(Web3.HTTPProvider(rpc_url), middleware=[ExtraDataToPOAMiddleware])
    assert w3.is_connected()

    return w3


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

    event = REG.MASTER_ACCOUNT_CONTROLLER.events["InstructionExecuted"]

    return wait_for_event(
        w3,
        event,
        (block, block + 4 * 90),
        lambda x: x["args"]["transactionId"].hex() == r.result["hash"].lower(),
        "waiting to bridge",
    )


def reserve_collateral(
    xrp: JsonRpcClient, agent_address: ChecksumAddress, lots: int
) -> Response:
    memo_data = encoder.reserve_collateral(agent_address, lots).hex()
    return bridge_tx(xrp, [memo(memo_data)])


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


def mint(globals: Globals, args: BridgeMint) -> None:
    w3 = globals.w3
    xrp = globals.xrp

    resp = reserve_collateral(xrp, args.agent_address, args.lots)
    bridged = bridge_pp(w3, resp)
    if bridged is None:
        print("failed to bridge")
        return
    bridged_tx_hash, bridged_tx_block = (
        bridged["transactionHash"].hex(),
        bridged["blockNumber"],
    )

    cr_event = REG.ASSET_MANAGER_EVENTS.events["CollateralReserved"]
    cr_log = next(
        scan_events(w3, (cr_event,), (bridged_tx_block, bridged_tx_block + 1))
    )
    data = get_event_data(w3.codec, cr_event.abi, cr_log)

    _args = data["args"]
    amount = str(_args["valueUBA"] + _args["feeUBA"])
    destination = _args["paymentAddress"]
    memos = [memo(_args["paymentReference"].hex())]
    last_ledger_sequence = _args["lastUnderlyingBlock"]
    collateral_reservation_id = _args["collateralReservationId"]

    input(
        "successful collateral resevation, continue to 2nd part of mint... press enter"
    )
    resp = send_xpr_tx(xrp, amount, destination, memos, last_ledger_sequence)
    print("sent underlying assets in", resp.result["hash"])
    print(f"https://testnet.xrpl.org/transactions/{resp.result['hash']}/detailed")

    me_event = REG.ASSET_MANAGER_EVENTS.events["MintingExecuted"]

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


def get_xrp_tx(xrp: JsonRpcClient, tx_hash: str):
    return xrp.request(Tx(transaction=tx_hash))


def deposit(globals: Globals, args: BridgeDeposit) -> None:
    memo_data = encoder.deposit(args.amount).hex()
    resp = bridge_tx(globals.xrp, [memo(memo_data)])
    bridge_pp(globals.w3, resp)


def withdraw(globals: Globals, args: BridgeWithdraw) -> None:
    memo_data = encoder.withdraw(args.amount).hex()
    resp = bridge_tx(globals.xrp, [memo(memo_data)])
    bridge_pp(globals.w3, resp)


def redeem(globals: Globals, args: BridgeRedeem) -> None:
    memo_data = encoder.deposit(args.lots).hex()
    resp = bridge_tx(globals.xrp, [memo(memo_data)])
    bridge_pp(globals.w3, resp)


def full_scenario(
    globals: Globals,
):
    mint(
        globals,
        BridgeMint(agent_address="0x55c815260cBE6c45Fe5bFe5FF32E3C7D746f14dC", lots=2),
    )
    print("minted fassets, check here:")
    print(
        "https://coston2-explorer.flare.network/address/0x0b6A3645c240605887a5532109323A3E12273dc7?tab=read_proxy"
    )
    print()
    input("continue to deposit... press enter")
    deposit(globals, BridgeDeposit(amount=1_000_000))
    print("deposited into vault, check here:")
    print(
        "https://coston2-explorer.flare.network/address/0x912DbF2173bD48ec0848357a128652D4c0fc33EB?tab=read_contract"
    )
    print()
    input("continue to withdraw... press enter")
    withdraw(globals, BridgeWithdraw(amount=1_000_000))
    print("withdrawn from vault, check here:")
    print(
        "https://coston2-explorer.flare.network/address/0x912DbF2173bD48ec0848357a128652D4c0fc33EB?tab=read_contract"
    )
    print()
    input("continue to redeem... press enter")
    redeem(globals, BridgeRedeem(lots=1))


def custom(globals: Globals, args: BridgeCustom) -> None:
    w3 = globals.w3
    pk = os.getenv("PRIVATE_KEY")
    assert pk
    addr = w3.eth.account.from_key(pk).address
    tx = (
        w3.eth.contract(
            address=REG.MASTER_ACCOUNT_CONTROLLER.address,
            abi=REG.MASTER_ACCOUNT_CONTROLLER.abi,
        )
        .functions.registerCustomInstruction((args.address, args.value, args.data))
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
    evnt = REG.MASTER_ACCOUNT_CONTROLLER.events["CustomInstructionRegistered"]
    evnt_log = next(scan_events(w3, (evnt,), (block, block + 1)))
    data = get_event_data(w3.codec, evnt.abi, evnt_log)
    call_hash = data["args"]["callHash"].to_bytes(31)
    memo_data = encoder.custom(call_hash).hex()
    resp = bridge_tx(globals.xrp, [memo(memo_data)])
    bridge_pp(w3, resp)


def fsa(env: ParsedEnv) -> None:
    globals = Globals(
        w3=get_w3_client(env.flr_rpc_url),
        xrp=JsonRpcClient(env.xrp_rpc_url),
        env=env,
    )

    args = cli.get_parser().parse_args()

    # TODO:(janezicmatej) figure out types
    bridge_resolver: dict[
        str, tuple[type[NamespaceSerializer], Callable[..., None]]
    ] = {
        "deposit": (BridgeDeposit, deposit),
        "withdraw": (BridgeWithdraw, withdraw),
        "redeem": (BridgeRedeem, redeem),
        "mint": (BridgeMint, mint),
        "custom": (BridgeCustom, custom),
    }

    match args.command:
        case "bridge":
            serializer, resolver = bridge_resolver[args.subcommand]
            resolver(globals, serializer.from_namespace(args))

        case "debug":
            match args.subcommand:
                case "full":
                    full_scenario(globals)

        case _:
            raise NotImplementedError()


def main() -> None:
    dotenv.load_dotenv()
    return fsa(ParsedEnv.from_env())


if __name__ == "__main__":
    main()
