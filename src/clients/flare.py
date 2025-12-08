from typing import Self

import web3
from eth_account import Account
from eth_account.signers.local import LocalAccount
from eth_typing import ChecksumAddress
from eth_utils.address import to_checksum_address
from web3 import middleware
from web3.types import TxParams

from src.registry import registry
from src.settings import settings


class Client:
    def __init__(self, rpc_url) -> None:
        self.client = web3.Web3(web3.Web3.HTTPProvider(rpc_url))
        self.client.middleware_onion.inject(
            middleware.ExtraDataToPOAMiddleware, layer=0
        )
        self.account: LocalAccount | None = None

    @classmethod
    def default(cls) -> Self:
        return cls(settings.env.flr_rpc_url)

    def inject_signer_middleware(self, pk: str) -> None:
        self.account = Account.from_key(pk)

        signer_mw = middleware.SignAndSendRawMiddlewareBuilder.build(self.account)
        self.client.middleware_onion.inject(signer_mw, layer=0)  # type: ignore

    def get_contract_address_by_name(self, name: str) -> ChecksumAddress:
        contract = self.client.eth.contract(
            address=registry.flare_contract_registry.address,
            abi=registry.flare_contract_registry.abi,
        )

        return to_checksum_address(
            contract.functions.getContractAddressByName(name).call()
        )

    def get_balance(self, evm_address: ChecksumAddress) -> int:
        return self.client.eth.get_balance(evm_address)

    def send_transaction(self, tx: TxParams) -> bytes:
        assert self.account is not None, "Signer middleware not injected."

        tx.setdefault("from", self.account.address)
        tx_hash = self.client.eth.send_transaction(tx)
        self.client.eth.wait_for_transaction_receipt(tx_hash)

        return tx_hash
