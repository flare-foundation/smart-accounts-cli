from eth_typing import ChecksumAddress


class InstructionId:
    Deposit = 1
    Withdraw = 2
    Approve = 3
    Redeem = 4
    ReserveCollateral = 5
    ClaimWithdraw = 6
    Custom = 99


def _encode(instruction_id: int, value: bytes) -> bytes:
    instruction = instruction_id.to_bytes(1) + value
    assert len(instruction) == 32, f"passed value length is {len(value)}"

    return instruction


def deposit(amount: int) -> bytes:
    value = amount.to_bytes(31)
    return _encode(instruction_id=InstructionId.Deposit, value=value)


def withdraw(amount: int) -> bytes:
    value = amount.to_bytes(31)
    return _encode(instruction_id=InstructionId.Withdraw, value=value)


def approve(amount: int) -> bytes:
    value = amount.to_bytes(31)
    return _encode(instruction_id=InstructionId.Approve, value=value)


def redeem(lots: int) -> bytes:
    value = lots.to_bytes(11) + 20 * b"\x00"
    return _encode(instruction_id=InstructionId.Redeem, value=value)


def reserve_collateral(agent_address: ChecksumAddress, lots: int) -> bytes:
    addr_bytes = bytes.fromhex(agent_address.removeprefix("0x"))
    value = lots.to_bytes(11) + addr_bytes
    return _encode(instruction_id=InstructionId.ReserveCollateral, value=value)


def custom(call_hash: bytes) -> bytes:
    return _encode(instruction_id=InstructionId.Custom, value=call_hash)
