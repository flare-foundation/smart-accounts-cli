import json
from typing import Self

import attrs
from eth_typing import ChecksumAddress
from eth_utils.address import to_checksum_address

from src.clients import flare
from src.registry import registry


@attrs.define
class ICollateralReserved:
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


class Client:
    def __init__(self, client: flare.Client, address: ChecksumAddress) -> None:
        self.client = client
        self.contract = self.client.client.eth.contract(
            address=address,
            abi=registry.asset_manager.abi,
        )
        self.events = self.client.client.eth.contract(
            address=address,
            abi=registry.asset_manager_events.abi,
        )

    @classmethod
    def default(cls) -> Self:
        return cls(flare.Client.default(), registry.asset_manager.address)

    def get_collateral_reservation_fee(self, lots: int) -> int:
        return self.contract.functions.collateralReservationFee(lots).call()

    def get_fxrp_balance(self, evm_address: ChecksumAddress) -> int:
        contract = self.client.client.eth.contract(
            # TODO:(@janezicmatej) read dynamically from assetmanager
            address=to_checksum_address("0x0b6A3645c240605887a5532109323A3E12273dc7"),
            abi=json.load(open("./artifacts/IErc20.json"))["abi"],
        )

        return contract.functions.balanceOf(evm_address).call()

    def get_fxrp_decimals(self) -> int:
        contract = self.client.client.eth.contract(
            # TODO:(@janezicmatej) read dynamically from assetmanager
            address=to_checksum_address("0x0b6A3645c240605887a5532109323A3E12273dc7"),
            abi=json.load(open("./artifacts/IErc20.json"))["abi"],
        )

        return contract.functions.decimals().call()

    def find_collateral_reserved_events(
        self,
        minter: ChecksumAddress,
        from_block: int,
        to_block: int | None = None,
    ) -> list[ICollateralReserved]:
        _to_block = self.client.client.eth.block_number
        to_block = min(to_block or _to_block, _to_block)

        events = []

        for b in range(from_block, to_block, 30):
            events.extend(
                self.events.events.CollateralReserved().get_logs(
                    from_block=b,
                    to_block=min(b + 29, to_block),
                    argument_filters={"minter": minter},
                )
            )

        ret = []

        for event in events:
            a = event["args"]
            ret.append(
                ICollateralReserved(
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
