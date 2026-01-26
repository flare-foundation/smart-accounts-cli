from typing import Self

from eth_typing import ChecksumAddress

from clients import mixins
from clients.flare import base, flare
from configuration.registry import registry


class Client(base.BaseContractClient, mixins.Erc20ContractMixin):
    @classmethod
    def default_with_address(cls, address: ChecksumAddress) -> Self:
        return cls(flare.Client.default(), address, registry.abis.upshift)
