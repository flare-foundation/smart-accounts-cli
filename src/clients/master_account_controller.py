import json
from typing import Self

import attrs
from eth_typing import ChecksumAddress

from src.clients import flare
from src.registry import registry


@attrs.frozen
class VaultInfo:
    id: int
    name: str
    type: int
    address: ChecksumAddress
    symbol: str
    decimals: int


@attrs.frozen
class AgentVaultInfo:
    id: int
    address: ChecksumAddress


class Client:
    def __init__(self, client: flare.Client, address: ChecksumAddress) -> None:
        self.client = client
        self.contract = self.client.client.eth.contract(
            address=address,
            abi=registry.master_account_controller.abi,
        )

        self._vault_cache: dict[int, VaultInfo] = {}
        self._agent_vault_cache: dict[int, AgentVaultInfo] = {}

    @classmethod
    def default(cls) -> Self:
        return cls(flare.Client.default(), registry.master_account_controller.address)

    def get_xrpl_provider_wallets(self) -> list[ChecksumAddress]:
        return self.contract.functions.getXrplProviderWallets().call()

    def get_personal_account(self, xrpl_address: str) -> ChecksumAddress:
        return self.contract.functions.getPersonalAccount(xrpl_address).call()

    def get_vaults(self) -> dict[int, VaultInfo]:
        vaults = self.contract.functions.getVaults().call()

        for i, address, vault_type in zip(vaults[0], vaults[1], vaults[2], strict=True):
            if i in self._vault_cache:
                continue

            name, symbol, decimals = self._get_vault_name_symbol_decimals(address)
            self._vault_cache[i] = VaultInfo(
                id=i,
                name=name,
                type=vault_type,
                address=address,
                symbol=symbol,
                decimals=decimals,
            )

        return self._vault_cache

    def _get_vault_contract(self, address: ChecksumAddress):
        return self.client.client.eth.contract(
            address=address,
            abi=json.load(open("artifacts/MyERC4626.json"))["abi"],
        )

    def _get_vault_name_symbol_decimals(
        self, address: ChecksumAddress
    ) -> tuple[str, str, int]:
        vault_contract = self._get_vault_contract(address)
        name = vault_contract.functions.name().call()
        symbol = vault_contract.functions.symbol().call()
        decimals = vault_contract.functions.decimals().call()
        return name, symbol, decimals

    def get_vault_balance(self, vault: VaultInfo, evm_address: ChecksumAddress) -> int:
        vault_contract = self._get_vault_contract(vault.address)
        balance = vault_contract.functions.balanceOf(evm_address).call()
        return balance

    def get_instruction_fee(self, instruction: int) -> int:
        return self.contract.functions.getInstructionFee(instruction).call()

    def get_agent_vaults(self) -> dict[int, AgentVaultInfo]:
        vaults = self.contract.functions.getAgentVaults().call()

        for i, address in zip(vaults[0], vaults[1], strict=True):
            if i in self._agent_vault_cache:
                continue
            self._agent_vault_cache[i] = AgentVaultInfo(id=i, address=address)

        return self._agent_vault_cache

    def get_executor_fee(self) -> int:
        return self.contract.functions.getExecutorInfo().call()[1]

    def get_transaction_id_for_collateral_reservation(
        self, collateral_reservation_id: int
    ) -> str:
        return (
            self.contract.functions.getTransactionIdForCollateralReservation(
                collateral_reservation_id
            )
            .call()
            .hex()
        )
