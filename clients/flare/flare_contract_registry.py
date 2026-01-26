from typing import Self

from eth_typing import ChecksumAddress
from eth_utils.address import to_checksum_address

from clients.flare import base, flare
from configuration.registry import registry


class Client(base.BaseContractClient):
    @classmethod
    def default(cls) -> Self:
        return cls(
            flare.Client.default(),
            registry.flare_contract_registry.address,
            registry.flare_contract_registry.abi,
        )

    def get_contract_address_by_name(self, name: str) -> ChecksumAddress:
        return to_checksum_address(
            self._contract.functions.getContractAddressByName(name).call()
        )
