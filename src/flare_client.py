import time
from collections.abc import Iterator, Sequence
from typing import Callable

from web3._utils.events import get_event_data
from web3.types import EventData, LogReceipt
from xrpl.models import Response
from xrpl.utils import ripple_time_to_posix

from src.registry import Event, registry
from src.settings import settings


def _scan_events(
    events: Sequence[Event], block_range: tuple[int, int]
) -> Iterator[LogReceipt]:
    w3 = settings.w3

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


def get_event(event: Event, block: int) -> LogReceipt:
    return next(_scan_events((event,), (block, block + 1)))


def find_block_near_timestamp(timestamp: int, tolerance: int = 10) -> int:
    w3 = settings.w3

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

        if abs(c["timestamp"] - timestamp) < tolerance:
            return c["number"]

        if c["timestamp"] > timestamp:
            (a, b) = (a, c)
        else:
            (a, b) = (c, b)


def wait_for_event(
    event: Event,
    block_range: tuple[int, int],
    filter_fn: Callable[[EventData], bool],
    message: str | None = None,
) -> EventData | None:
    w3 = settings.w3

    print(message, end="", flush=True)
    while True:
        if message is not None:
            print(".", end="", flush=True)

        for e in _scan_events((event,), block_range):
            data = get_event_data(w3.codec, event.abi, e)
            if filter_fn(data):
                print()
                return data

        if w3.eth.block_number > block_range[1]:
            break

        time.sleep(10)

    print()


def wait_until_bridged(r: Response) -> EventData | None:
    block = find_block_near_timestamp(
        ripple_time_to_posix(r.result["tx_json"]["date"]) - 90
    )

    event = registry.master_account_controller.events["InstructionExecuted"]

    return wait_for_event(
        event,
        (block, block + 4 * 90),
        lambda x: x["args"]["transactionId"].hex() == r.result["hash"].lower(),
        "waiting to bridge",
    )
