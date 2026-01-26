from typing import Self

from eth_account import Account
from eth_account.signers.local import LocalAccount
from eth_typing import ChecksumAddress
from web3 import middleware
from web3.types import Nonce, TxParams, Wei

from clients.flare import base
from configuration.settings import settings


class Client(base.BaseClient):
    @classmethod
    def default(cls) -> Self:
        return cls(settings.flr_rpc_url)

    def get_balance(self, evm_address: ChecksumAddress) -> int:
        return self._client.eth.get_balance(evm_address)

    def find_block_near_timestamp(self, timestamp: int, tolerance: int = 10) -> int:
        b = self._client.eth.get_block("latest")
        assert "timestamp" in b and "number" in b
        assert timestamp < b["timestamp"]

        p_sample = self._client.eth.get_block(b["number"] - 1_000_000)
        assert "timestamp" in p_sample and "number" in p_sample

        production_per_s = (b["number"] - p_sample["number"]) / (
            b["timestamp"] - p_sample["timestamp"]
        )

        a = self._client.eth.get_block(
            b["number"] - int((b["timestamp"] - timestamp) * production_per_s) * 2
        )
        assert "timestamp" in a and "number" in a
        assert timestamp > a["timestamp"]

        while True:
            c_block = (b["number"] + a["number"]) // 2
            c = self._client.eth.get_block(c_block)
            assert "timestamp" in c and "number" in c

            if abs(c["timestamp"] - timestamp) < tolerance:
                return c["number"]

            if c["timestamp"] > timestamp:
                (a, b) = (a, c)
            else:
                (a, b) = (c, b)


class SigningClient(Client):
    def __init__(self, rpc_url: str, pk: str) -> None:
        super().__init__(rpc_url)

        self._account: LocalAccount = Account.from_key(pk)
        self._nonce = self._client.eth.get_transaction_count(self._account.address)

        signer_mw = middleware.SignAndSendRawMiddlewareBuilder.build(self._account)
        self._client.middleware_onion.inject(signer_mw, layer=0)  # type: ignore

    @classmethod
    def default_with_pk(cls, pk: str) -> Self:
        return cls(settings.flr_rpc_url, pk)

    @classmethod
    def default(cls) -> Self:
        raise NotImplementedError("Use `default_with_pk` method instead.")

    def _build_tx(
        self,
        tx_params: TxParams,
    ) -> TxParams:
        tx_params.setdefault("from", self._account.address)
        tx_params.setdefault("value", Wei(0))

        block = self._client.eth.get_block("latest")
        base_fee = block["baseFeePerGas"]  # type: ignore
        max_priority_fee = self._client.eth.max_priority_fee
        max_fee_per_gas = base_fee * 2 + max_priority_fee

        gas_limit = int(self._client.eth.estimate_gas(tx_params) * 1.5)
        tx: TxParams = {
            **tx_params,
            # we don't expect these to be set before sending and we override them
            "nonce": Nonce(self._nonce),
            "chainId": self._client.eth.chain_id,
            "type": 2,
            "gas": gas_limit,
            "maxFeePerGas": Wei(max_fee_per_gas),
            "maxPriorityFeePerGas": max_priority_fee,
        }

        return tx

    def send_transaction(self, tx: TxParams) -> bytes:
        tx = self._build_tx(tx)
        tx_hash = self._client.eth.send_transaction(tx)

        self._client.eth.wait_for_transaction_receipt(tx_hash)
        self._nonce += 1

        return tx_hash
