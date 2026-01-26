from py_flare_common.smart_accounts.encoder import instructions


def encode_omni(args: instructions.InstructionAbc):
    return print(f"0x{args.encode().hex()}")
