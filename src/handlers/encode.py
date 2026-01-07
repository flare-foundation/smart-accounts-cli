from src import encoder


def encode_omni(args: encoder.InstructionAbc):
    return print(f"0x{args.encode().hex()}")
