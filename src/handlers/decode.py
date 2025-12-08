from src import encoder
from src.cli.types import DecodeInstruction


def decode_instruction(args: DecodeInstruction):
    print(encoder.Instruction.decode(args.instruction).decode(args.instruction))
