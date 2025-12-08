import json
from typing import Any, Self

import attrs
from eth_typing import ChecksumAddress
from web3.types import TxParams

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

        # TODO:(@janezicmatej) ask if vaults on some id could change
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

    def reserve_collateral(
        self, xrpl_address: str, payment_reference: bytes, transaction_id: bytes
    ) -> TxParams:
        # TODO:(@janezicmatej) figure out why this failed and then how to figure
        # out the gas estimation (i think it's because this client doesn't have
        # signer middleware injected)
        return self.contract.functions.reserveCollateral(
            xrpl_address, payment_reference, transaction_id
        ).build_transaction({"gas": 2_000_000})

    def execute_instruction(self, proof: dict[str, Any], xrpl_address: str) -> TxParams:
        return self.contract.functions.executeInstruction(
            proof, xrpl_address
        ).build_transaction({"gas": 2_000_000})

    def execute_deposit_after_minting(
        self, collateral_reservation_id: int, proof: dict[str, Any], xrpl_address: str
    ) -> TxParams:
        return self.contract.functions.executeDepositAfterMinting(
            collateral_reservation_id, proof, xrpl_address
        ).build_transaction()

    def is_transaction_id_used(self, transaction_id: bytes) -> bool:
        return self.contract.functions.isTransactionIdUsed(transaction_id).call()
