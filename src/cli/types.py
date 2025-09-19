import argparse
import json
import sys
from typing import Any, Callable, Self

import attrs
from eth_typing import ChecksumAddress
from eth_utils.address import to_checksum_address
from web3.types import Wei

from src import xrpl_client


def value_parser(value: str | Wei) -> Wei:
    try:
        return Wei(int(value))
    except ValueError:
        pass

    assert isinstance(value, str)

    if value.endswith("wei"):
        try:
            return Wei(int(value.removesuffix("wei")))
        except ValueError:
            pass

    if value.endswith("flr"):
        try:
            return Wei(int(value.removesuffix("flr")) * 10**18)
        except ValueError:
            pass

    raise ValueError(
        f"invalid {value=} for wei: should be number or end with wei or flr"
    )


def list_map_converter[T, U](mapper: Callable[[T], U]) -> Callable[[list[T]], list[U]]:
    def wrapped(item_list: list[T]) -> list[U]:
        return [mapper(i) for i in item_list]

    return wrapped


def json_read_file_or_stdin(path: str | None) -> Any:
    if path is None:
        return []

    if path == "-":
        file = sys.stdin
    else:
        file = open(path)

    return json.load(file)


def bytes_parser(b: str | bytes) -> bytes:
    if isinstance(b, bytes):
        return b
    return bytes.fromhex(b.removeprefix("0x"))


class NamespaceSerializer:
    @classmethod
    def from_namespace(cls, namespace: argparse.Namespace) -> Self:
        return cls(
            **{
                a.name: getattr(namespace, a.name)
                for a in cls.__attrs_attrs__  # type: ignore
                if a.init
            }
        )


@attrs.frozen(kw_only=True)
class Bridge:
    pass


@attrs.frozen(kw_only=True)
class BridgeDeposit(Bridge, NamespaceSerializer):
    amount: int


@attrs.frozen(kw_only=True)
class BridgeWithdraw(Bridge, NamespaceSerializer):
    amount: int


@attrs.frozen(kw_only=True)
class BridgeRedeem(Bridge, NamespaceSerializer):
    lots: int


@attrs.frozen(kw_only=True)
class BridgeMint(Bridge, NamespaceSerializer):
    agent_address: ChecksumAddress = attrs.field(converter=to_checksum_address)
    lots: int


@attrs.frozen(kw_only=True)
class BridgeClaimWithdraw(Bridge, NamespaceSerializer):
    # reward_epoch: int
    pass


@attrs.frozen
class CustomInstruction:
    address: ChecksumAddress = attrs.field(converter=to_checksum_address)
    value: Wei = attrs.field(converter=value_parser)
    data: bytes = attrs.field(converter=bytes_parser)


@attrs.frozen(kw_only=True)
class BridgeCustom(NamespaceSerializer):
    address: list[ChecksumAddress] = attrs.field(
        converter=list_map_converter(to_checksum_address)
    )
    value: list[Wei] = attrs.field(converter=list_map_converter(value_parser))
    data: list[bytes] = attrs.field(converter=list_map_converter(bytes_parser))
    json: Any = attrs.field(converter=json_read_file_or_stdin)
    serialized: list[CustomInstruction] = attrs.field(init=False)

    def __attrs_post_init__(self):
        if len(self.address) != len(self.value) or len(self.value) != len(self.data):
            raise ValueError(
                "length of passed addresses, values and data must be equal"
            )

        if self.address and self.json:
            raise ValueError(
                "can't parse json file and flag parameters at the same time"
            )

        if not self.address and not self.json:
            raise ValueError("must pass json file or flag paramteres")

        object.__setattr__(
            self,
            "serialized",
            [
                *[CustomInstruction(**obj) for obj in self.json],
                *[
                    CustomInstruction(*t)
                    for t in zip(self.address, self.value, self.data)
                ],
            ],
        )


@attrs.frozen(kw_only=True)
class DebugMockCreateFund(NamespaceSerializer):
    seed: str
    value: Wei = attrs.field(converter=value_parser)


@attrs.frozen(kw_only=True)
class DebugCheckStatus(NamespaceSerializer):
    xrpl_hash: bytes = attrs.field(converter=bytes_parser)


@attrs.frozen(kw_only=True)
class DebugSimulation(NamespaceSerializer):
    agent_address: ChecksumAddress = attrs.field(converter=to_checksum_address)
    mint: int
    deposit: int


@attrs.frozen(kw_only=True)
class DebugMockCustom(NamespaceSerializer):
    seed: str
    address: list[ChecksumAddress] = attrs.field(
        converter=list_map_converter(to_checksum_address)
    )
    value: list[Wei] = attrs.field(converter=list_map_converter(value_parser))
    data: list[bytes] = attrs.field(converter=list_map_converter(bytes_parser))
    json: Any = attrs.field(converter=json_read_file_or_stdin)
    serialized: list[CustomInstruction] = attrs.field(init=False)

    def __attrs_post_init__(self):
        if len(self.address) != len(self.value) or len(self.value) != len(self.data):
            raise ValueError(
                "length of passed addresses, values and data must be equal"
            )

        if self.address and self.json:
            raise ValueError(
                "can't parse json file and flag parameters at the same time"
            )

        if not self.address and not self.json:
            raise ValueError("must pass json file or flag paramteres")

        object.__setattr__(
            self,
            "serialized",
            [
                *[CustomInstruction(**obj) for obj in self.json],
                *[
                    CustomInstruction(*t)
                    for t in zip(self.address, self.value, self.data)
                ],
            ],
        )


@attrs.frozen(kw_only=True)
class PersonalAccount:
    from_env: bool


@attrs.frozen(kw_only=True)
class PersonalAccountPrint(PersonalAccount, NamespaceSerializer):
    xrpl_address: str | None
    xrpl_address_parsed: str = attrs.field(init=False)

    def __attrs_post_init__(self):
        if self.xrpl_address is None and not self.from_env:
            raise ValueError("--from-env/-e must be passed if xrpl_address is omitted")

        if self.xrpl_address and self.from_env:
            raise ValueError(
                "cannot read value from environment and command line at the same time"
            )

        object.__setattr__(
            self,
            "xrpl_address_parsed",
            xrpl_client.get_wallet().address,
        )


@attrs.frozen(kw_only=True)
class PersonalAccountFaucet(PersonalAccount, NamespaceSerializer):
    xrpl_address: str | None
    xrpl_address_parsed: str = attrs.field(init=False)

    def __attrs_post_init__(self):
        if self.xrpl_address is None and not self.from_env:
            raise ValueError("--from-env/-e must be passed if xrpl_address is omitted")

        if self.xrpl_address and self.from_env:
            raise ValueError(
                "cannot read value from environment and command line at the same time"
            )

        object.__setattr__(
            self,
            "xrpl_address_parsed",
            xrpl_client.get_wallet().address,
        )
