from typing import Self

import attrs

from clients.flare import base, flare
from configuration.registry import registry

XRP_USD_FEED_ID = bytes.fromhex("015852502f55534400000000000000000000000000")
FLR_USD_FEED_ID = bytes.fromhex("01464c522f55534400000000000000000000000000")


@attrs.frozen
class FtsoFeed:
    value: int
    decimals: int
    timestamp: int


class Client(base.BaseContractClient):
    @classmethod
    def default(cls) -> Self:
        return cls(
            flare.Client.default(),
            registry.ftso_v2.address,
            registry.ftso_v2.abi,
        )

    def get_feed_by_id(self, feed_id: bytes) -> FtsoFeed:
        data = self._contract.functions.getFeedById(feed_id).call()

        return FtsoFeed(
            value=data[0],
            decimals=data[1],
            timestamp=data[2],
        )

    def get_feed_xrp_usd(self) -> FtsoFeed:
        return self.get_feed_by_id(XRP_USD_FEED_ID)

    def get_feed_flr_usd(self) -> FtsoFeed:
        return self.get_feed_by_id(FLR_USD_FEED_ID)
