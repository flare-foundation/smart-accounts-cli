import functools


class Erc20ContractMixin:
    @functools.cached_property
    def name(self) -> str:
        return self._contract.functions.name().call()

    @functools.cached_property
    def symbol(self) -> str:
        return self._contract.functions.symbol().call()

    @functools.cached_property
    def decimals(self) -> int:
        return self._contract.functions.decimals().call()

    @functools.cached_property
    def total_supply(self) -> int:
        return self._contract.functions.totalSupply().call()

    def balance_of(self, address: str) -> int:
        return self._contract.functions.balanceOf(address).call()
