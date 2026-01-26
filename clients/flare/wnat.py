from typing import Self

from web3.types import TxParams

from clients.flare import base, flare
from configuration.registry import registry


class Client(base.BaseContractClient):
    @classmethod
    def default(cls) -> Self:
        return cls(
            flare.Client.default(),
            registry.wnat.address,
            registry.wnat.abi,
        )

    def get_balance(self, address: str) -> int:
        return self._contract.functions.balanceOf(address).call()

    def transfer_wnat(self, address: str, amount: int) -> TxParams:
        return self._encode_tx(
            "transfer",
            [address, amount],
        )
