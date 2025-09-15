import argparse


def get_parser() -> argparse.ArgumentParser:
    cli = argparse.ArgumentParser(prog="fsa")

    subcli = cli.add_subparsers(title="command", required=True, dest="command")

    b_cli = subcli.add_parser("bridge", help="flare smart accounts system interface")
    b_cli.add_argument(
        "-s",
        "--silent",
        action="store_true",
        default=False,
        required=False,
        help="silent mode",
    )
    b_cli.add_argument(
        "-W",
        "--no-wait",
        action="store_true",
        default=False,
        required=False,
        help="don't wait for bridge confirmation",
    )

    b_subcli = b_cli.add_subparsers(required=True, dest="subcommand")

    b_deposit = b_subcli.add_parser("deposit", help="deposit fassets into vault")
    b_deposit.add_argument(
        "-a",
        "--amount",
        type=int,
        required=True,
        help="number of tokens to deposit to vault",
        metavar="",
    )

    b_withdraw = b_subcli.add_parser("withdraw", help="withdraw fassets from vault")
    b_withdraw.add_argument(
        "-a",
        "--amount",
        type=int,
        required=True,
        help="number of tokens to withdraw from vault",
        metavar="",
    )

    b_redeem = b_subcli.add_parser("redeem", help="redeem fassets")
    b_redeem.add_argument(
        "-l",
        "--lots",
        type=int,
        required=True,
        help="number of lots to redeem",
        metavar="",
    )

    b_mint = b_subcli.add_parser("mint", help="reserve collateral and send underlying")
    b_mint.add_argument(
        "-a",
        "--agent-address",
        type=str,
        required=True,
        help="agent address to mint with",
        metavar="",
    )
    b_mint.add_argument(
        "-l",
        "--lots",
        type=int,
        required=True,
        help="number of lots to mint",
        metavar="",
    )

    b_claim_withdraw = b_subcli.add_parser(
        "claim-withdraw", help="claim withdrawal of fassets from vault"
    )
    b_claim_withdraw.add_argument(
        "-r",
        "--reward-epoch",
        type=int,
        required=True,
        help=(
            "which reward epoch to claim withdrawal for"
            " - mock implementation will accept any value"
        ),
        metavar="",
    )

    b_custom_instruction = b_subcli.add_parser("custom", help="send custom instruction")
    b_custom_instruction.add_argument(
        "-a",
        "--address",
        action="append",
        type=str,
        required=False,
        default=[],
        help="flare transaction target address",
        metavar="",
    )
    b_custom_instruction.add_argument(
        "-v",
        "--value",
        action="append",
        type=str,
        required=False,
        default=[],
        help="flare transaction value, 'flr' can be appended for flare units",
        metavar="",
    )
    b_custom_instruction.add_argument(
        "-d",
        "--data",
        action="append",
        type=str,
        required=False,
        help="flare transaction calldata hex encoded",
        default=[],
        metavar="",
    )
    b_custom_instruction.add_argument(
        "json",
        nargs="?",
        type=str,
        help="json file to read, if '-' is passed stdin is read instead",
    )

    d_cli = subcli.add_parser("debug", help="utility functions for bridge info")

    d_subcli = d_cli.add_subparsers(required=True, dest="subcommand")

    d_subcli.add_parser(
        "full", help="run full scenario - mint, deposit, withdraw, redeem"
    )

    d_check_status = d_subcli.add_parser(
        "check-status", help="check bridge status of xrpl transaction"
    )
    d_check_status.add_argument(
        "xrpl_hash",
        type=str,
        help="xrpl transaction hash to be checked",
    )

    return cli
