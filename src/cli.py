import argparse


def get_cli_parser() -> argparse.ArgumentParser:
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

    # b_mint = b_subcli.add_parser(
    #     "mint",
    #     help="reserve collateral and send underlying",
    # )
    # b_deposit = b_subcli.add_parser("deposit", help="deposit fassets into vault")
    # b_withdraw = b_subcli.add_parser("withdraw", help="withdraw fassets from vault")
    # b_redeem = b_subcli.add_parser("redeem", help="redeem fassets")

    b_custom_instruction = b_subcli.add_parser("custom", help="send custom instruction")
    b_custom_instruction.add_argument(
        "-a",
        "--address",
        type=str,
        required=True,
        help="flare transaction target address",
        metavar="",
    )
    b_custom_instruction.add_argument(
        "-v",
        "--value",
        type=int,
        required=True,
        help="flare transaction value",
        metavar="",
    )
    b_custom_instruction.add_argument(
        "-d",
        "--data",
        type=str,
        required=True,
        help="flare transaction calldata hex encoded",
        metavar="",
    )

    d_cli = subcli.add_parser("debug", help="utility functions for bridge info")
    d_subcli = d_cli.add_subparsers(required=True, dest="subcommand")
    d_subcli.add_parser(
        "full", help="run full scenario - mint, deposit, withdraw, redeem"
    )

    return cli
