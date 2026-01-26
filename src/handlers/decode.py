from py_flare_common.smart_accounts.encoder import decoder

from src.cli.types import DecodeInstruction


def decode_instruction(args: DecodeInstruction):
    d = decoder.Decoder.with_all_instructions()
    print(d.decode(args.instruction).decode(args.instruction))
