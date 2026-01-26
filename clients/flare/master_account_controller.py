from typing import Any, Self

import attrs
from eth_typing import ABI, ChecksumAddress
from web3.types import EventData, TxParams

from clients.flare import base, firelight, flare, upshift
from configuration.registry import registry


class VaultType:
    FIRELIGHT = 1
    UPSHIFT = 2


@attrs.frozen
class VaultInfo:
    id: int
    address: ChecksumAddress
    type: int


@attrs.frozen
class AgentVaultInfo:
    id: int
    address: ChecksumAddress


@attrs.define
class RedeemRequested:
    personal_account: ChecksumAddress
    vault: ChecksumAddress
    shares: int
    claimable_epoch: int
    year: int
    month: int
    day: int

    @classmethod
    def from_event_data(cls, event_data: EventData) -> Self:
        a = event_data["args"]
        return cls(
            personal_account=a["personalAccount"],
            vault=a["vault"],
            shares=a["shares"],
            claimable_epoch=a["claimableEpoch"],
            year=a["year"],
            month=a["month"],
            day=a["day"],
        )


class Client(base.BaseContractClient):
    def __init__(
        self, client: base.BaseClient, address: ChecksumAddress, abi: ABI
    ) -> None:
        super().__init__(client, address, abi)

        self._upshift_client: dict[int, upshift.Client] = {}
        self._firelight_client: dict[int, firelight.Client] = {}

        self._agent_vault_cache: dict[int, AgentVaultInfo] = {}
        self._vault_cache: dict[int, VaultInfo] = {}

    @classmethod
    def default(cls) -> Self:
        return cls(
            flare.Client.default(),
            registry.master_account_controller.address,
            registry.master_account_controller.abi,
        )

    # XrplProviderWalletsFacet

    def get_xrpl_provider_wallets(self) -> list[ChecksumAddress]:
        return self._contract.functions.getXrplProviderWallets().call()

    # PersonalAccountsFacet

    def get_personal_account(self, xrpl_address: str) -> ChecksumAddress:
        return self._contract.functions.getPersonalAccount(xrpl_address).call()

    # VaultsFacet

    def cached_get_firelight_client(self, vault: VaultInfo) -> firelight.Client:
        assert vault.type == VaultType.FIRELIGHT

        if vault.id not in self._firelight_client:
            client = firelight.Client.default_with_address(vault.address)
            self._firelight_client[vault.id] = client

        return self._firelight_client[vault.id]

    def cached_get_upshift_client(self, vault: VaultInfo) -> upshift.Client:
        assert vault.type == VaultType.UPSHIFT

        if vault.id not in self._upshift_client:
            client = upshift.Client.default_with_address(vault.address)
            self._upshift_client[vault.id] = client

        return self._upshift_client[vault.id]

    def cached_get_vault_client(
        self, vault: VaultInfo
    ) -> upshift.Client | firelight.Client:
        if vault.type == VaultType.FIRELIGHT:
            return self.cached_get_firelight_client(vault)
        elif vault.type == VaultType.UPSHIFT:
            return self.cached_get_upshift_client(vault)
        raise ValueError(f"unknown vault type: {vault.type}")

    def get_vaults(self) -> dict[int, VaultInfo]:
        vaults = self._contract.functions.getVaults().call()

        for i, address, vault_type in zip(vaults[0], vaults[1], vaults[2], strict=True):
            if i in self._vault_cache:
                continue
            self._vault_cache[i] = VaultInfo(id=i, address=address, type=vault_type)

        return self._vault_cache

    # InstructionsFeesFacet

    def get_instruction_fee(self, instruction: int) -> int:
        return self._contract.functions.getInstructionFee(instruction).call()

    # AgentVaultsFacet

    def get_agent_vaults(self) -> dict[int, AgentVaultInfo]:
        vaults = self._contract.functions.getAgentVaults().call()

        for i, address in zip(vaults[0], vaults[1], strict=True):
            if i in self._agent_vault_cache:
                continue
            self._agent_vault_cache[i] = AgentVaultInfo(id=i, address=address)

        return self._agent_vault_cache

    # ExecutorsFacet

    def get_executor_fee(self) -> int:
        return self._contract.functions.getExecutorInfo().call()[1]

    # InstructionsFacet

    def is_transaction_id_used(self, transaction_id: bytes) -> bool:
        return self._contract.functions.isTransactionIdUsed(transaction_id).call()

    def reserve_collateral(
        self, xrpl_address: str, payment_reference: bytes, transaction_id: bytes
    ) -> TxParams:
        return self._encode_tx(
            "reserveCollateral",
            [xrpl_address, payment_reference, transaction_id],
        )

    def execute_instruction(self, proof: dict[str, Any], xrpl_address: str) -> TxParams:
        return self._encode_tx(
            "executeInstruction",
            [proof, xrpl_address],
        )

    def execute_deposit_after_minting(
        self, collateral_reservation_id: int, proof: dict[str, Any], xrpl_address: str
    ) -> TxParams:
        return self._encode_tx(
            "executeDepositAfterMinting",
            [collateral_reservation_id, proof, xrpl_address],
        )

    # CustomInstructionsFacet

    def encode_custom_instruction(
        self, custom_instruction: list[dict[str, Any]]
    ) -> bytes:
        return self._contract.functions.encodeCustomInstruction(
            custom_instruction
        ).call()

    def get_custom_instruction(self, custom_instruction_hash: bytes) -> bytes:
        return self._contract.functions.getCustomInstruction(
            custom_instruction_hash
        ).call()

    def register_custom_instruction(
        self, custom_instruction: list[dict[str, Any]]
    ) -> TxParams:
        return self._encode_tx(
            "registerCustomInstruction",
            [custom_instruction],
        )

    # events

    def get_redeem_requested_event(self, tx_hash: bytes) -> RedeemRequested:
        return RedeemRequested.from_event_data(
            self._extract_event_from_tx(
                tx_hash,
                self._contract.events.RedeemRequested(),
            )
        )

    def get_transaction_id_for_collateral_reservation(
        self, collateral_reservation_id: int
    ) -> str:
        return (
            self._contract.functions.getTransactionIdForCollateralReservation(
                collateral_reservation_id
            )
            .call()
            .hex()
        )
