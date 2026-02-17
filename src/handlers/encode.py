from py_flare_common.smart_accounts.encoder import instructions

from configuration.settings import settings


def encode_omni(args: instructions.InstructionAbc):
    object.__setattr__(args, "wallet_id", settings.chain_config.wallet_id)
    return print(f"0x{args.encode().hex()}")
