import argparse
import json
import sys
from collections.abc import Callable
from typing import Any, Self, TypeVar

import attrs
from web3.types import Wei

from src import encoder


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


T = TypeVar("T")
U = TypeVar("U")


def list_map_converter(mapper: Callable[[T], U]) -> Callable[[list[T]], list[U]]:
    def wrapped(item_list: list[T]) -> list[U]:
        return [mapper(i) for i in item_list]

    return wrapped


def str_or_stdin(s: str) -> str:
    if s == "-":
        return sys.stdin.read().rstrip()
    return s


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
class Encode:
    pass


@attrs.frozen(kw_only=True)
class EncodeFxrpCr(Encode, encoder.FxrpCollateralReservation, NamespaceSerializer):
    pass


@attrs.frozen(kw_only=True)
class EncodeFxrpTransfer(Encode, encoder.FxrpTransfer, NamespaceSerializer):
    pass


@attrs.frozen(kw_only=True)
class EncodeFxrpRedeem(Encode, encoder.FxrpRedeem, NamespaceSerializer):
    pass


@attrs.frozen(kw_only=True)
class EncodeFirelightCrDeposit(
    Encode, encoder.FirelightCollateralReservationAndDeposit, NamespaceSerializer
):
    pass


@attrs.frozen(kw_only=True)
class EncodeFirelightDeposit(Encode, encoder.FirelightDeposit, NamespaceSerializer):
    pass


@attrs.frozen(kw_only=True)
class EncodeFirelightRedeem(Encode, encoder.FirelightRedeem, NamespaceSerializer):
    pass


@attrs.frozen(kw_only=True)
class EncodeFirelightClaimWithdraw(
    Encode, encoder.FirelightClaimWithdraw, NamespaceSerializer
):
    pass


@attrs.frozen(kw_only=True)
class EncodeUpshiftCrDeposit(
    Encode, encoder.UpshiftCollateralReservationAndDeposit, NamespaceSerializer
):
    pass


@attrs.frozen(kw_only=True)
class EncodeUpshiftDeposit(Encode, encoder.UpshiftDeposit, NamespaceSerializer):
    pass


@attrs.frozen(kw_only=True)
class EncodeUpshiftRequestRedeem(
    Encode, encoder.UpshiftRequestRedeem, NamespaceSerializer
):
    pass


@attrs.frozen(kw_only=True)
class EncodeUpshiftClaim(Encode, encoder.UpshiftClaim, NamespaceSerializer):
    pass


@attrs.frozen(kw_only=True)
class Decode:
    pass


@attrs.frozen(kw_only=True)
class DecodeInstruction(Decode, NamespaceSerializer):
    instruction: str = attrs.field(converter=str_or_stdin)


@attrs.frozen(kw_only=True)
class Bridge:
    pass


def hexstr_validator(instance: Any, attribute: attrs.Attribute, value: str) -> None:
    try:
        bytes.fromhex(value.removeprefix("0x"))

    except ValueError as e:
        raise ValueError(f"{attribute.name} must be a valid hex string") from e


@attrs.frozen(kw_only=True)
class BridgeInstruction(Bridge, NamespaceSerializer):
    instruction: str = attrs.field(validator=hexstr_validator, converter=str_or_stdin)


@attrs.frozen(kw_only=True)
class BridgeMintTx(Bridge, NamespaceSerializer):
    wait: bool
    xrpl_hash: str = attrs.field(validator=hexstr_validator, converter=str_or_stdin)
