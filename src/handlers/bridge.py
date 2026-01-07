import sys
import time

from xrpl.utils import ripple_time_to_posix

from src.cli.types import BridgeInstruction, BridgeMintTx
from src.clients import asset_manager, flare, master_account_controller, xrpl
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

    print(f"sent bridge instruction transaction: {tx.result['hash']}", file=sys.stderr)
    print(tx.result["hash"])


def bridge_mint_tx(args: BridgeMintTx):
    mac = master_account_controller.Client.default()
    am = asset_manager.Client.default()
    f = flare.Client.default()
    x = xrpl.Client.default()

    xrpl_tx = x.get_tx(args.xrpl_hash.removeprefix("0x")).result

    xrpl_time = ripple_time_to_posix(xrpl_tx["tx_json"]["date"])
    # subst 90 seconds to account for possible network time lag
    flare_block = f.find_block_near_timestamp(xrpl_time - 90)

    minter = mac.get_personal_account(xrpl_tx["tx_json"]["Account"])

    crts = am.find_collateral_reserved_events(
        minter, flare_block, flare_block + 10 * 60
    )

    crt = None
    for c in crts:
        mapped_hash = mac.get_transaction_id_for_collateral_reservation(
            c.collateral_reservation_id
        ).upper()

        if mapped_hash.upper() == args.xrpl_hash.upper():
            crt = c
            break

    if crt is None and args.wait:
        for _ in range(12):
            time.sleep(5)
            crts = am.find_collateral_reserved_events(
                minter, flare_block, flare_block + 10 * 60
            )
            for c in crts:
                mapped_hash = mac.get_transaction_id_for_collateral_reservation(
                    c.collateral_reservation_id
                ).upper()

                if mapped_hash.upper() == args.xrpl_hash.upper():
                    crt = c
                    break

            if crt is not None:
                break

    if crt is None:
        print("could not find matching CollateralReserved event", file=sys.stderr)
        return

    tx = x.send_tx(
        amount=crt.value_uba + crt.fee_uba,
        fee=10,
        destination=crt.payment_address,
        memos=crt.payment_reference.hex(),
        last_ledger_sequence=crt.last_underlying_block,
    )

    print(f"sent mint tx: {tx.result['hash']}", file=sys.stderr)
    print(tx.result["hash"])
