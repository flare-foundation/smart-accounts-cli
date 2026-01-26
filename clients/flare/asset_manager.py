from typing import Self

import attrs
from eth_typing import ChecksumAddress
from eth_utils.address import to_checksum_address
from web3.types import EventData

from clients.flare import base, flare, fxrp
from configuration.registry import registry


@attrs.define
class CollateralReserved:
    agent_vault: ChecksumAddress
    minter: ChecksumAddress
    collateral_reservation_id: int
    value_uba: int
    fee_uba: int
    first_underlying_block: int
    last_underlying_block: int
    last_underlying_timestamp: int
    payment_address: str
    payment_reference: bytes
    executor: ChecksumAddress
    executor_fee_nat_wei: int

    @classmethod
    def from_event_data(cls, event_data: EventData) -> Self:
        a = event_data["args"]
        return cls(
            agent_vault=a["agentVault"],
            minter=a["minter"],
            collateral_reservation_id=a["collateralReservationId"],
            value_uba=a["valueUBA"],
            fee_uba=a["feeUBA"],
            first_underlying_block=a["firstUnderlyingBlock"],
            last_underlying_block=a["lastUnderlyingBlock"],
            last_underlying_timestamp=a["lastUnderlyingTimestamp"],
            payment_address=a["paymentAddress"],
            payment_reference=a["paymentReference"],
            executor=a["executor"],
            executor_fee_nat_wei=a["executorFeeNatWei"],
        )


class Client(base.BaseContractClient):
    @classmethod
    def default(cls) -> Self:
        return cls(
            flare.Client.default(),
            registry.asset_manager.address,
            registry.asset_manager.abi,
        )

    # SettingsReaderFacet

    def fasset(self) -> ChecksumAddress:
        return to_checksum_address(self._contract.functions.fAsset().call())

    def get_fxrp_client(self) -> fxrp.Client:
        return fxrp.Client.default_with_address(self.fasset())

    # CollateralReservationsFacet

    def collateral_reservation_fee(self, lots: int) -> int:
        return self._contract.functions.collateralReservationFee(lots).call()

    # Events

    def get_collateral_reserved_event(self, tx_hash: bytes) -> CollateralReserved:
        return CollateralReserved.from_event_data(
            self._extract_event_from_tx(
                tx_hash,
                self._contract.events.CollateralReserved(),
            )
        )

    def emergency_paused(self) -> bool:
        return self._contract.functions.emergencyPaused.call()

    def find_collateral_reserved_events(
        self,
        minter: ChecksumAddress,
        from_block: int,
        to_block: int | None = None,
    ) -> list[CollateralReserved]:
        _to_block = self._client._client.eth.block_number
        to_block = min(to_block or _to_block, _to_block)

        events = []

        for b in range(from_block, to_block, 30):
            events.extend(
                self._contract.events.CollateralReserved().get_logs(
                    from_block=b,
                    to_block=min(b + 29, to_block),
                    argument_filters={"minter": minter},
                )
            )

        ret = []

        for event in events:
            a = event["args"]
            ret.append(
                CollateralReserved(
                    agent_vault=a["agentVault"],
                    minter=a["minter"],
                    collateral_reservation_id=a["collateralReservationId"],
                    value_uba=a["valueUBA"],
                    fee_uba=a["feeUBA"],
                    first_underlying_block=a["firstUnderlyingBlock"],
                    last_underlying_block=a["lastUnderlyingBlock"],
                    last_underlying_timestamp=a["lastUnderlyingTimestamp"],
                    payment_address=a["paymentAddress"],
                    payment_reference=a["paymentReference"],
                    executor=a["executor"],
                    executor_fee_nat_wei=a["executorFeeNatWei"],
                )
            )

        return ret
