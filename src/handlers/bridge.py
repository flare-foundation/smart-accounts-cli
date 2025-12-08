from src.cli.types import BridgeInstruction
from src.clients import master_account_controller, xrpl
from src.encoder import Instruction


def bridge_instruction(args: BridgeInstruction):
    mac = master_account_controller.Client.default()
    x = xrpl.Client.default()

    instruction_cls = Instruction.decode(args.instruction)
    instruction_cls.decode(args.instruction)

    fee = mac.get_instruction_fee(instruction_cls.INSTRUCTION_ID)

    tx = x.send_tx(
        amount=fee,
        fee="10",
        destination=mac.get_xrpl_provider_wallets()[0],
        memos=args.instruction.removeprefix("0x"),
    )

    print(f"sent bridge request: {tx.result['hash']}")
