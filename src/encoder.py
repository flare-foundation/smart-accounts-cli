# payment reference format (32 bytes):
# instruction id consists of instruction type (4 bits) and instruction command (4 bits)

# FXRP (instruction type 0)
# bytes 00: bytes1 (hex) -> instruction id
#     00: collateral reservation
#     01: transfer
#     02: redeem
# bytes 01: uint8 -> wallet identifier
# collateral reservation:
# bytes 02-11: uint80 -> value (lots)
# bytes 12-13: uint16 -> agent vault address id (collateral reservation)
# transfer:
# bytes 02-11: uint80 -> value (amount in drops)
# bytes 12-31: address (20 bytes) -> recipient address
# redeem:
# bytes 02-11: uint80 -> value (lots)

# Firelight vaults (instruction type 1)
# bytes 00: bytes1 (hex) -> instruction id
#     10: collateral reservation and deposit
#     11: deposit
#     12: redeem
#     13: claim withdraw
# bytes 01: uint8 -> wallet identifier
# collateral reservation and deposit:
# bytes 02-11: uint80 -> value (lots)
# bytes 12-13: uint16 -> agent vault address id
# bytes 14-15: uint16 -> deposit vault address id
# deposit:
# bytes 02-11: uint80 -> value (assets in drops)
# bytes 14-15: uint16 -> deposit vault address id
# redeem:
# bytes 02-11: uint80 -> value (shares in drops)
# bytes 14-15: uint16 -> withdraw vault address id
# claim withdraw:
# bytes 02-11: uint80 -> value (period)
# bytes 14-15: uint16 -> withdraw vault address id

# Upshift vaults (instruction type 2)
# bytes 00: bytes1 (hex) -> instruction id
#     20: collateral reservation and deposit
#     21: deposit
#     22: requestRedeem
#     23: claim
# bytes 01: uint8 -> wallet identifier
# collateral reservation and deposit:
# bytes 02-11: uint80 -> value (lots)
# bytes 12-13: uint16 -> agent vault address id
# bytes 14-15: uint16 -> deposit vault address id
# deposit:
# bytes 02-11: uint80 -> value (assets in drops)
# bytes 14-15: uint16 -> deposit vault address id
# requestRedeem:
# bytes 02-11: uint80 -> value (shares in drops)
# bytes 14-15: uint16 -> withdraw vault address id
# claim:
# bytes 02-11: uint80 -> value (date(yyyymmdd))
# bytes 14-15: uint16 -> withdraw vault address id

import abc
import datetime
from collections.abc import Callable
from typing import Any, ClassVar, Self

import attrs
from eth_typing import ChecksumAddress
from eth_utils.address import to_checksum_address


class DecodeError(Exception):
    pass


class EncodeError(Exception):
    pass


def _clean_str_or_bytes(s: str | bytes) -> bytes:
    if isinstance(s, bytes):
        return s

    try:
        return bytes.fromhex(s.removeprefix("0x"))
    except ValueError as e:
        raise DecodeError(f"invalid hex string: {s}") from e


class InstructionAbc(abc.ABC):
    INSTRUCTION_ID: ClassVar[int]

    @abc.abstractmethod
    def encode(self) -> bytes: ...

    @classmethod
    @abc.abstractmethod
    def decode(cls, b: bytes | str) -> Self: ...


def make_uint_validator(bits: int) -> Callable[[Any, Any, int], None]:
    def validator(instance, attribute, value):
        max_value = (1 << bits) - 1

        if not isinstance(value, int):
            raise EncodeError(f"{attribute.name} must be an integer")

        if not (0 <= value <= max_value):
            raise EncodeError(
                f"{attribute.name} must be between 0 and {max_value} (inclusive)"
            )

    return validator


@attrs.frozen
class FxrpCollateralReservation(InstructionAbc):
    INSTRUCTION_ID = 0x00

    wallet_id: int = attrs.field(validator=make_uint_validator(8))
    value: int = attrs.field(validator=make_uint_validator(80))
    agent_vault_id: int = attrs.field(validator=make_uint_validator(16))

    def encode(self) -> bytes:
        b = bytearray(32)
        b[0] = self.INSTRUCTION_ID
        b[1] = self.wallet_id
        b[2:12] = self.value.to_bytes(10, "big")
        b[12:14] = self.agent_vault_id.to_bytes(2, "big")
        return bytes(b)

    @classmethod
    def decode(cls, b: bytes | str) -> Self:
        b = _clean_str_or_bytes(b)
        if len(b) != 32:
            raise DecodeError("must be 32 bytes")

        if b[0] != cls.INSTRUCTION_ID:
            raise DecodeError("invalid instruction id")

        wallet_id = b[1]
        value = int.from_bytes(b[2:12], "big")
        agent_vault_id = int.from_bytes(b[12:14], "big")

        return cls(
            wallet_id=wallet_id,
            value=value,
            agent_vault_id=agent_vault_id,
        )


def checksum_address_validator(
    instance: Any, attribute: Any, value: ChecksumAddress
) -> None:
    try:
        to_checksum_address(value)
    except ValueError as e:
        raise EncodeError(f"{attribute.name} must be a valid checksum address") from e


@attrs.frozen
class FxrpTransfer(InstructionAbc):
    INSTRUCTION_ID = 0x01

    wallet_id: int = attrs.field(validator=make_uint_validator(8))
    value: int = attrs.field(validator=make_uint_validator(80))
    recipient_address: ChecksumAddress = attrs.field(
        validator=checksum_address_validator
    )

    def encode(self) -> bytes:
        if len(self.recipient_address) != 20:
            raise EncodeError("recipient_address must be 20 bytes")

        b = bytearray(32)
        b[0] = self.INSTRUCTION_ID
        b[1] = self.wallet_id
        b[2:12] = self.value.to_bytes(10, "big")
        b[12:32] = bytes.fromhex(self.recipient_address.removeprefix("0x"))
        return bytes(b)

    @classmethod
    def decode(cls, b: bytes | str) -> Self:
        b = _clean_str_or_bytes(b)
        if len(b) != 32:
            raise DecodeError("must be 32 bytes")

        if b[0] != cls.INSTRUCTION_ID:
            raise DecodeError("invalid instruction id")

        wallet_id = b[1]
        value = int.from_bytes(b[2:12], "big")
        recipient_address = to_checksum_address(b[12:32].hex())

        return cls(
            wallet_id=wallet_id,
            value=value,
            recipient_address=recipient_address,
        )


@attrs.frozen
class FxrpRedeem(InstructionAbc):
    INSTRUCTION_ID = 0x02

    wallet_id: int = attrs.field(validator=make_uint_validator(8))
    value: int = attrs.field(validator=make_uint_validator(80))

    def encode(self) -> bytes:
        b = bytearray(32)
        b[0] = self.INSTRUCTION_ID
        b[1] = self.wallet_id
        b[2:12] = self.value.to_bytes(10, "big")
        return bytes(b)

    @classmethod
    def decode(cls, b: bytes | str) -> Self:
        b = _clean_str_or_bytes(b)
        if len(b) != 32:
            raise DecodeError("must be 32 bytes")

        if b[0] != cls.INSTRUCTION_ID:
            raise DecodeError("invalid instruction id")

        wallet_id = b[1]
        value = int.from_bytes(b[2:12], "big")

        return cls(
            wallet_id=wallet_id,
            value=value,
        )


@attrs.frozen
class FirelightCollateralReservationAndDeposit(InstructionAbc):
    INSTRUCTION_ID = 0x10

    wallet_id: int = attrs.field(validator=make_uint_validator(8))
    value: int = attrs.field(validator=make_uint_validator(80))
    agent_vault_id: int = attrs.field(validator=make_uint_validator(16))
    vault_id: int = attrs.field(validator=make_uint_validator(16))

    def encode(self) -> bytes:
        b = bytearray(32)
        b[0] = self.INSTRUCTION_ID
        b[1] = self.wallet_id
        b[2:12] = self.value.to_bytes(10, "big")
        b[12:14] = self.agent_vault_id.to_bytes(2, "big")
        b[14:16] = self.vault_id.to_bytes(2, "big")
        return bytes(b)

    @classmethod
    def decode(cls, b: bytes | str) -> Self:
        b = _clean_str_or_bytes(b)
        if len(b) != 32:
            raise DecodeError("must be 32 bytes")

        if b[0] != cls.INSTRUCTION_ID:
            raise DecodeError("invalid instruction id")

        wallet_id = b[1]
        value = int.from_bytes(b[2:12], "big")
        agent_vault_id = int.from_bytes(b[12:14], "big")
        vault_id = int.from_bytes(b[14:16], "big")

        return cls(
            wallet_id=wallet_id,
            value=value,
            agent_vault_id=agent_vault_id,
            vault_id=vault_id,
        )


@attrs.frozen
class FirelightDeposit(InstructionAbc):
    INSTRUCTION_ID = 0x11

    wallet_id: int = attrs.field(validator=make_uint_validator(8))
    value: int = attrs.field(validator=make_uint_validator(80))
    vault_id: int = attrs.field(validator=make_uint_validator(16))

    def encode(self) -> bytes:
        b = bytearray(32)
        b[0] = self.INSTRUCTION_ID
        b[1] = self.wallet_id
        b[2:12] = self.value.to_bytes(10, "big")
        b[14:16] = self.vault_id.to_bytes(2, "big")
        return bytes(b)

    @classmethod
    def decode(cls, b: bytes | str) -> Self:
        b = _clean_str_or_bytes(b)
        if len(b) != 32:
            raise DecodeError("must be 32 bytes")

        if b[0] != cls.INSTRUCTION_ID:
            raise DecodeError("invalid instruction id")

        wallet_id = b[1]
        value = int.from_bytes(b[2:12], "big")
        vault_id = int.from_bytes(b[14:16], "big")

        return cls(
            wallet_id=wallet_id,
            value=value,
            vault_id=vault_id,
        )


@attrs.frozen
class FirelightRedeem(InstructionAbc):
    INSTRUCTION_ID = 0x12

    wallet_id: int = attrs.field(validator=make_uint_validator(8))
    value: int = attrs.field(validator=make_uint_validator(80))
    vault_id: int = attrs.field(validator=make_uint_validator(16))

    def encode(self) -> bytes:
        b = bytearray(32)
        b[0] = self.INSTRUCTION_ID
        b[1] = self.wallet_id
        b[2:12] = self.value.to_bytes(10, "big")
        b[14:16] = self.vault_id.to_bytes(2, "big")
        return bytes(b)

    @classmethod
    def decode(cls, b: bytes | str) -> Self:
        b = _clean_str_or_bytes(b)
        if len(b) != 32:
            raise DecodeError("must be 32 bytes")

        if b[0] != cls.INSTRUCTION_ID:
            raise DecodeError("invalid instruction id")

        wallet_id = b[1]
        value = int.from_bytes(b[2:12], "big")
        vault_id = int.from_bytes(b[14:16], "big")

        return cls(
            wallet_id=wallet_id,
            value=value,
            vault_id=vault_id,
        )


@attrs.frozen
class FirelightClaimWithdraw(InstructionAbc):
    INSTRUCTION_ID = 0x13

    wallet_id: int = attrs.field(validator=make_uint_validator(8))
    value: int = attrs.field(validator=make_uint_validator(80))
    vault_id: int = attrs.field(validator=make_uint_validator(16))

    def encode(self) -> bytes:
        b = bytearray(32)
        b[0] = self.INSTRUCTION_ID
        b[1] = self.wallet_id
        b[2:12] = self.value.to_bytes(10, "big")
        b[14:16] = self.vault_id.to_bytes(2, "big")
        return bytes(b)

    @classmethod
    def decode(cls, b: bytes | str) -> Self:
        b = _clean_str_or_bytes(b)
        if len(b) != 32:
            raise DecodeError("must be 32 bytes")

        if b[0] != cls.INSTRUCTION_ID:
            raise DecodeError("invalid instruction id")

        wallet_id = b[1]
        value = int.from_bytes(b[2:12], "big")
        vault_id = int.from_bytes(b[14:16], "big")

        return cls(
            wallet_id=wallet_id,
            value=value,
            vault_id=vault_id,
        )


@attrs.frozen
class UpshiftCollateralReservationAndDeposit(InstructionAbc):
    INSTRUCTION_ID = 0x20

    wallet_id: int = attrs.field(validator=make_uint_validator(8))
    value: int = attrs.field(validator=make_uint_validator(80))
    agent_vault_id: int = attrs.field(validator=make_uint_validator(16))
    vault_id: int = attrs.field(validator=make_uint_validator(16))

    def encode(self) -> bytes:
        b = bytearray(32)
        b[0] = self.INSTRUCTION_ID
        b[1] = self.wallet_id
        b[2:12] = self.value.to_bytes(10, "big")
        b[12:14] = self.agent_vault_id.to_bytes(2, "big")
        b[14:16] = self.vault_id.to_bytes(2, "big")
        return bytes(b)

    @classmethod
    def decode(cls, b: bytes | str) -> Self:
        b = _clean_str_or_bytes(b)
        if len(b) != 32:
            raise DecodeError("must be 32 bytes")

        if b[0] != cls.INSTRUCTION_ID:
            raise DecodeError("invalid instruction id")

        wallet_id = b[1]
        value = int.from_bytes(b[2:12], "big")
        agent_vault_id = int.from_bytes(b[12:14], "big")
        vault_id = int.from_bytes(b[14:16], "big")

        return cls(
            wallet_id=wallet_id,
            value=value,
            agent_vault_id=agent_vault_id,
            vault_id=vault_id,
        )


@attrs.frozen
class UpshiftDeposit(InstructionAbc):
    INSTRUCTION_ID = 0x21

    wallet_id: int = attrs.field(validator=make_uint_validator(8))
    value: int = attrs.field(validator=make_uint_validator(80))
    vault_id: int = attrs.field(validator=make_uint_validator(16))

    def encode(self) -> bytes:
        b = bytearray(32)
        b[0] = self.INSTRUCTION_ID
        b[1] = self.wallet_id
        b[2:12] = self.value.to_bytes(10, "big")
        b[14:16] = self.vault_id.to_bytes(2, "big")
        return bytes(b)

    @classmethod
    def decode(cls, b: bytes | str) -> Self:
        b = _clean_str_or_bytes(b)
        if len(b) != 32:
            raise DecodeError("must be 32 bytes")

        if b[0] != cls.INSTRUCTION_ID:
            raise DecodeError("invalid instruction id")

        wallet_id = b[1]
        value = int.from_bytes(b[2:12], "big")
        vault_id = int.from_bytes(b[14:16], "big")

        return cls(
            wallet_id=wallet_id,
            value=value,
            vault_id=vault_id,
        )


@attrs.frozen
class UpshiftRequestRedeem(InstructionAbc):
    INSTRUCTION_ID = 0x22

    wallet_id: int = attrs.field(validator=make_uint_validator(8))
    value: int = attrs.field(validator=make_uint_validator(80))
    vault_id: int = attrs.field(validator=make_uint_validator(16))

    def encode(self) -> bytes:
        b = bytearray(32)
        b[0] = self.INSTRUCTION_ID
        b[1] = self.wallet_id
        b[2:12] = self.value.to_bytes(10, "big")
        b[14:16] = self.vault_id.to_bytes(2, "big")
        return bytes(b)

    @classmethod
    def decode(cls, b: bytes | str) -> Self:
        b = _clean_str_or_bytes(b)
        if len(b) != 32:
            raise DecodeError("must be 32 bytes")

        if b[0] != cls.INSTRUCTION_ID:
            raise DecodeError("invalid instruction id")

        wallet_id = b[1]
        value = int.from_bytes(b[2:12], "big")
        vault_id = int.from_bytes(b[14:16], "big")

        return cls(
            wallet_id=wallet_id,
            value=value,
            vault_id=vault_id,
        )


def date_to_yyyymmdd(date: datetime.date | int) -> int:
    if isinstance(date, int):
        return date

    return date.year * 10000 + date.month * 100 + date.day


def yyyymmdd_to_date(yyyymmdd: int | str | datetime.date) -> datetime.date:
    if isinstance(yyyymmdd, datetime.date):
        return yyyymmdd

    if isinstance(yyyymmdd, str):
        yyyymmdd = int(yyyymmdd)

    year = (yyyymmdd // 10000) % 10000
    month = (yyyymmdd // 100) % 100
    day = yyyymmdd % 100

    return datetime.date(year, month, day)


@attrs.frozen
class UpshiftClaim(InstructionAbc):
    INSTRUCTION_ID = 0x23

    wallet_id: int = attrs.field(validator=make_uint_validator(8))
    value: datetime.date = attrs.field(converter=yyyymmdd_to_date)
    vault_id: int = attrs.field(validator=make_uint_validator(16))

    def encode(self) -> bytes:
        b = bytearray(32)
        b[0] = self.INSTRUCTION_ID
        b[1] = self.wallet_id
        b[2:12] = date_to_yyyymmdd(self.value).to_bytes(10, "big")
        b[14:16] = self.vault_id.to_bytes(2, "big")
        return bytes(b)

    @classmethod
    def decode(cls, b: bytes | str) -> Self:
        b = _clean_str_or_bytes(b)
        if len(b) != 32:
            raise DecodeError("must be 32 bytes")

        if b[0] != cls.INSTRUCTION_ID:
            raise DecodeError("invalid instruction id")

        wallet_id = b[1]
        value = yyyymmdd_to_date(int.from_bytes(b[2:12], "big"))
        vault_id = int.from_bytes(b[14:16], "big")

        return cls(
            wallet_id=wallet_id,
            value=value,
            vault_id=vault_id,
        )


class Instruction:
    @classmethod
    def all(cls) -> list[type[InstructionAbc]]:
        return [
            # fxrp
            FxrpCollateralReservation,
            FxrpTransfer,
            FxrpRedeem,
            # firelight
            FirelightCollateralReservationAndDeposit,
            FirelightDeposit,
            FirelightRedeem,
            FirelightClaimWithdraw,
            # upshift
            UpshiftCollateralReservationAndDeposit,
            UpshiftDeposit,
            UpshiftRequestRedeem,
            UpshiftClaim,
        ]

    @classmethod
    def decode(cls, b: bytes | str) -> type[InstructionAbc]:
        b = _clean_str_or_bytes(b)
        if len(b) != 32:
            raise DecodeError("must be 32 bytes")

        for instruction_cls in cls.all():
            if b[0] == instruction_cls.INSTRUCTION_ID:
                return instruction_cls

        raise DecodeError("invalid instruction id")
