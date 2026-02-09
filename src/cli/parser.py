import argparse
import datetime

import attrs

from src.cli.types import (
    EncodeCustomInstruction,
    EncodeFirelightClaimWithdraw,
    EncodeFirelightCrDeposit,
    EncodeFirelightDeposit,
    EncodeFirelightRedeem,
    EncodeFxrpCr,
    EncodeFxrpRedeem,
    EncodeFxrpTransfer,
    EncodeUpshiftClaim,
    EncodeUpshiftCrDeposit,
    EncodeUpshiftDeposit,
    EncodeUpshiftRequestRedeem,
    NamespaceSerializer,
)


def _apply_arguments(argp: argparse.ArgumentParser, acls: type[NamespaceSerializer]):
    s = set()

    a: attrs.Attribute
    for a in attrs.fields(acls):
        if not a.init:
            continue

        short = None
        for c in a.name.replace("_", ""):
            if c not in s:
                short = c
                s.add(c)
                break

        args = []

        if short is not None:
            args.append(f"-{short}")

        args.append(f"--{a.name.replace('_', '-')}")

        type = a.type
        if type is None:
            return

        if type in [datetime.date]:
            type = int

        argp.add_argument(
            *args,
            type=type,
            required=True,
            help=f"{a.name.replace('_', ' ')} argument",
            metavar="",
        )


def get_parser() -> argparse.ArgumentParser:
    cli = argparse.ArgumentParser(prog="smart_accounts")
    cli.add_argument("--version", "-V", action="version", version="%(prog)s v0.1.0")

    subcli = cli.add_subparsers(
        title="command", required=True, dest="command", metavar=""
    )

    # encode cli
    e_cli = subcli.add_parser("encode", help="encode instructions")

    e_subcli = e_cli.add_subparsers(required=True, dest="subcommand", metavar="")

    e_fxrpcr = e_subcli.add_parser("fxrp-cr", help="mint fassets")
    _apply_arguments(e_fxrpcr, EncodeFxrpCr)

    e_fxrptransfer = e_subcli.add_parser("fxrp-transfer", help="transfer fassets")
    _apply_arguments(e_fxrptransfer, EncodeFxrpTransfer)

    e_fxrpredeem = e_subcli.add_parser("fxrp-redeem", help="redeem fassets")
    _apply_arguments(e_fxrpredeem, EncodeFxrpRedeem)

    e_firelightcrdeposit = e_subcli.add_parser(
        "firelight-cr-deposit", help="mint and deposit into vault"
    )
    _apply_arguments(e_firelightcrdeposit, EncodeFirelightCrDeposit)

    e_firelightdeposit = e_subcli.add_parser(
        "firelight-deposit", help="deposit fassets into vault"
    )
    _apply_arguments(e_firelightdeposit, EncodeFirelightDeposit)

    e_firelightredeem = e_subcli.add_parser(
        "firelight-redeem", help="request withdrawal from vault"
    )
    _apply_arguments(e_firelightredeem, EncodeFirelightRedeem)

    e_firelightclaimwithdraw = e_subcli.add_parser(
        "firelight-claim-withdraw", help="claim withdrawal from vault"
    )
    _apply_arguments(e_firelightclaimwithdraw, EncodeFirelightClaimWithdraw)

    e_upshiftcrdeposit = e_subcli.add_parser(
        "upshift-cr-deposit", help="mint and deposit into vault"
    )
    _apply_arguments(e_upshiftcrdeposit, EncodeUpshiftCrDeposit)

    e_upshiftdeposit = e_subcli.add_parser(
        "upshift-deposit", help="deposit fassets into vault"
    )
    _apply_arguments(e_upshiftdeposit, EncodeUpshiftDeposit)

    e_upshiftrequestredeem = e_subcli.add_parser(
        "upshift-request-redeem", help="request withdrawal from vault"
    )
    _apply_arguments(e_upshiftrequestredeem, EncodeUpshiftRequestRedeem)

    e_upshiftclaim = e_subcli.add_parser(
        "upshift-claim", help="claim withdrawal from vault"
    )
    _apply_arguments(e_upshiftclaim, EncodeUpshiftClaim)

    e_custominstruction = e_subcli.add_parser(
        "custom-instruction", help="send custom instruction"
    )
    _apply_arguments(e_custominstruction, EncodeCustomInstruction)

    d_cli = subcli.add_parser("decode", help="decode instructions")
    d_cli.add_argument(
        "instruction", type=str, help="hex encoded instruction to decode or - for stdin"
    )

    # bridge
    b_cli = subcli.add_parser("bridge", help="bridge related commands")

    b_subcli = b_cli.add_subparsers(required=True, dest="subcommand", metavar="")

    b_deposit = b_subcli.add_parser("instruction", help="send bridge request")
    b_deposit.add_argument(
        "instruction",
        type=str,
        help="hex encoded bridge instruction to send or - for stdin",
    )

    b_deposit = b_subcli.add_parser(
        "mint-tx", help="send mint transaction for bridge transaction"
    )
    b_deposit.add_argument(
        "-w",
        "--wait",
        action="store_true",
        help="wait for operator to perform collateral reservation",
    )
    b_deposit.add_argument(
        "xrpl_hash",
        type=str,
        help="hex encoded bridge transaction to mint for or - for stdin",
    )

    # custom
    c_cli = subcli.add_parser("custom", help="custom instruction related commands")

    c_subcli = c_cli.add_subparsers(required=True, dest="subcommand", metavar="")

    c_register = c_subcli.add_parser("register", help="register custom instruction")
    c_register.add_argument(
        "custom_instruction",
        type=str,
        help="custom instruction json to send or - for stdin",
    )

    return cli
