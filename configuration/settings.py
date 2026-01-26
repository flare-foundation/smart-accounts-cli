import os
from typing import Self

import attrs
import web3
from eth_typing import ChecksumAddress
from eth_utils.address import to_checksum_address
from web3 import middleware

import configuration.utils


@attrs.frozen(kw_only=True)
class ChainConfig:
    master_account_controller: ChecksumAddress

    @classmethod
    def from_chain_id(cls, chain_id: int, deployment_name: str | None) -> Self:
        match (chain_id, deployment_name):
            case (114, None) | (114, "production"):
                return cls(
                    master_account_controller=to_checksum_address(
                        "0x434936d47503353f06750Db1A444DBDC5F0AD37c"
                    ),
                )

            case (114, "staging"):
                return cls(
                    master_account_controller=to_checksum_address(
                        "0x32F662C63c1E24bB59B908249962F00B61C6638f"
                    ),
                )

        raise ValueError(
            f"configuration ({chain_id=}, {deployment_name=}) not supported"
        )


@attrs.frozen(kw_only=True)
class Settings:
    flr_rpc_url: str
    xrpl_rpc_url: str

    flr_private_key: str
    xrpl_seed: str

    chain_config: ChainConfig

    @classmethod
    def default(cls) -> Self:
        # TODO:(@janezicmatej) read all possible env variables for any mode of running
        # here instaead of django.conf.settigns
        deployment_name = os.getenv("DEPLOYMENT_NAME")
        flr_rpc_url = os.environ["FLR_RPC_URL"]
        xrpl_rpc_url = os.environ["XRPL_RPC_URL"]

        flr_private_key = os.environ["FLR_PRIVATE_KEY"]
        xrpl_seed = os.environ["XRPL_SECRET"]

        client = web3.Web3(web3.Web3.HTTPProvider(flr_rpc_url))
        client.middleware_onion.inject(
            middleware.ExtraDataToPOAMiddleware,
            layer=0,
        )

        chain_id = client.eth.chain_id

        return cls(
            flr_rpc_url=flr_rpc_url,
            xrpl_rpc_url=xrpl_rpc_url,
            flr_private_key=flr_private_key,
            xrpl_seed=xrpl_seed,
            chain_config=ChainConfig.from_chain_id(chain_id, deployment_name),
        )


settings = configuration.utils.wrap_singleton(Settings.default)
