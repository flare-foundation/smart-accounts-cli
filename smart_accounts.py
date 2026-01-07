#!/usr/bin/env python
from collections.abc import Callable
from typing import Any, TypeVar

import dotenv

from src import cli, handlers
from src.cli import types as ct


def not_implemented(args: Any) -> int | None:
    print(args)
    print("error: not implemented")
    return 2


T = TypeVar("T", bound=ct.NamespaceSerializer)
ResolverFn = tuple[type[T], Callable[[T], int | None]]
Resolver = dict[str, ResolverFn]


def smart_accounts() -> None:
    args = cli.get_parser().parse_args()

    resolver: dict[str, Resolver | ResolverFn] = {
        "encode": {
            "fxrp-cr": (ct.EncodeFxrpCr, handlers.encode.encode_omni),
            "fxrp-transfer": (ct.EncodeFxrpTransfer, handlers.encode.encode_omni),
            "fxrp-redeem": (ct.EncodeFxrpRedeem, handlers.encode.encode_omni),
            "firelight-cr-deposit": (
                ct.EncodeFirelightCrDeposit,
                handlers.encode.encode_omni,
            ),
            "firelight-deposit": (
                ct.EncodeFirelightDeposit,
                handlers.encode.encode_omni,
            ),
            "firelight-redeem": (ct.EncodeFirelightRedeem, handlers.encode.encode_omni),
            "firelight-claim-withdraw": (
                ct.EncodeFirelightClaimWithdraw,
                handlers.encode.encode_omni,
            ),
            "upshift-cr-deposit": (
                ct.EncodeUpshiftCrDeposit,
                handlers.encode.encode_omni,
            ),
            "upshift-deposit": (ct.EncodeUpshiftDeposit, handlers.encode.encode_omni),
            "upshift-request-redeem": (
                ct.EncodeUpshiftRequestRedeem,
                handlers.encode.encode_omni,
            ),
            "upshift-claim": (ct.EncodeUpshiftClaim, handlers.encode.encode_omni),
        },
        "decode": (ct.DecodeInstruction, handlers.decode.decode_instruction),
        "bridge": {
            "instruction": (ct.BridgeInstruction, handlers.bridge.bridge_instruction),
            "mint-tx": (ct.BridgeMintTx, handlers.bridge.bridge_mint_tx),
        },
    }

    r = resolver.get(args.command, {})
    if isinstance(r, dict):
        r = r.get(args.subcommand)

    if r is None:
        exit(not_implemented(args))

    serializer, resolver_fn = r
    # try:
    exit_code = resolver_fn(serializer.from_namespace(args))
    if exit_code is not None:
        exit(exit_code)
    # except ValueError as e:
    #     print(f"error: {', '.join(map(str, e.args))}", file=sys.stderr)
    #     exit(2)


def main() -> None:
    dotenv.load_dotenv()
    return smart_accounts()


if __name__ == "__main__":
    main()
