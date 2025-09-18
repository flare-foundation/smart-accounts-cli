import os
from typing import Callable, Self, cast

import attrs
from web3 import Web3
from web3.middleware.proof_of_authority import ExtraDataToPOAMiddleware
from xrpl.clients import JsonRpcClient


@attrs.frozen(kw_only=True)
class ParsedEnv:
    xrp_seed: str
    flr_private_key: str
    flr_rpc_url: str
    xrp_rpc_url: str

    @classmethod
    def from_env(cls) -> Self:
        # TODO:(janezicmatej) add validation and nice error
        xrp_seed = os.environ["XRP_SEED"]
        flr_private_key = os.environ["FLR_PRIVATE_KEY"]
        flr_rpc_url = os.environ["FLR_RPC_URL"]
        xrp_rpc_url = os.environ["XRP_RPC_URL"]

        return cls(
            xrp_seed=xrp_seed,
            flr_private_key=flr_private_key,
            flr_rpc_url=flr_rpc_url,
            xrp_rpc_url=xrp_rpc_url,
        )


@attrs.frozen(kw_only=True)
class Settings:
    w3: Web3
    xrp: JsonRpcClient
    env: ParsedEnv

    @classmethod
    def default(cls) -> Self:
        env = ParsedEnv.from_env()

        w3 = Web3(
            Web3.HTTPProvider(env.flr_rpc_url), middleware=[ExtraDataToPOAMiddleware]
        )
        assert w3.is_connected()

        return cls(
            w3=w3,
            xrp=JsonRpcClient(env.xrp_rpc_url),
            env=env,
        )


class SettingsWrapper:
    def __init__(self, factory: Callable[[], Settings]) -> None:
        self.factory = factory
        self.globals: Settings | None = None

    def __getattr__(self, *args, **kwargs):
        if self.globals is None:
            self.globals = self.factory()

        return getattr(self.globals, *args, **kwargs)


settings = cast(Settings, SettingsWrapper(Settings.default))
