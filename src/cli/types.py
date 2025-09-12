import argparse
from typing import Self

import attrs
from eth_typing import ChecksumAddress
from eth_utils.address import to_checksum_address
from web3.types import Wei


class NamespaceSerializer:
    @classmethod
    def from_namespace(cls, namespace: argparse.Namespace) -> Self:
        return cls(**{a.name: getattr(namespace, a.name) for a in cls.__attrs_attrs__})  # type: ignore


@attrs.frozen
class BridgeDeposit(NamespaceSerializer):
    amount: int


@attrs.frozen
class BridgeWithdraw(NamespaceSerializer):
    amount: int


@attrs.frozen
class BridgeRedeem(NamespaceSerializer):
    lots: int


@attrs.frozen
class BridgeMint(NamespaceSerializer):
    agent_address: ChecksumAddress = attrs.field(converter=to_checksum_address)
    lots: int


def value_parser(value: str) -> Wei:
    try:
        return Wei(int(value))
    except ValueError:
        pass

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


@attrs.frozen
class BridgeCustom(NamespaceSerializer):
    address: ChecksumAddress = attrs.field(converter=to_checksum_address)
    value: Wei = attrs.field(converter=value_parser)
    data: bytes = attrs.field(converter=bytes.fromhex)
