import time
from typing import Self

import attrs
from eth_typing import ChecksumAddress
from web3.types import EventData

from clients import mixins
from clients.flare import base, flare
from configuration.registry import registry


@attrs.frozen
class WithdrawRequest:
    sender: ChecksumAddress
    receiver: ChecksumAddress
    owner: ChecksumAddress
    period: int
    assets: int
    shares: int

    @classmethod
    def from_event_data(cls, event_data: EventData) -> Self:
        a = event_data["args"]
        return cls(
            sender=a["sender"],
            receiver=a["receiver"],
            owner=a["owner"],
            period=a["period"],
            assets=a["assets"],
            shares=a["shares"],
        )


@attrs.frozen
class PeriodConfiguration:
    epoch: int
    duration: int
    starting_period: int


class Client(base.BaseContractClient, mixins.Erc20ContractMixin):
    @classmethod
    def default_with_address(cls, address: ChecksumAddress) -> Self:
        return cls(flare.Client.default(), address, registry.abis.firelight)

    def get_withdraw_request_event(self, tx_hash: bytes) -> WithdrawRequest:
        return WithdrawRequest.from_event_data(
            self._extract_event_from_tx(
                tx_hash,
                self._contract.events.WithdrawRequest(),
            )
        )

    def current_period_configuration(self) -> PeriodConfiguration:
        config = self._contract.functions.currentPeriodConfiguration().call()
        return PeriodConfiguration(
            epoch=config[0],
            duration=config[1],
            starting_period=config[2],
        )

    def period_to_timestamp(self, period: int) -> int:
        # FIX:(@janezicmatej) this is here temporarily, until we have this method in the
        # staging environment.
        return int(time.time()) + 24 * 60 * 60

        config = self.current_period_configuration()
        return config.epoch + config.duration * (period - config.starting_period)
