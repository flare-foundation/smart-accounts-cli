import web3
from eth_typing import ABI, ChecksumAddress
from hexbytes import HexBytes
from web3 import middleware
from web3._utils.events import EventLogErrorFlags
from web3.contract.contract import Contract, ContractEvent
from web3.types import EventData, TxParams, TxReceipt


class BaseClient:
    def __init__(self, rpc_url: str):
        self._client = web3.Web3(web3.Web3.HTTPProvider(rpc_url))
        self._client.middleware_onion.inject(
            middleware.ExtraDataToPOAMiddleware,
            layer=0,
        )
        self._client.middleware_onion.remove("gas_price_strategy")
        self._client.middleware_onion.remove("gas_estimate")

    def get_contract(self, address: ChecksumAddress, abi: ABI) -> Contract:
        return self._client.eth.contract(address=address, abi=abi)


class BaseContractClient:
    def __init__(self, client: BaseClient, address: ChecksumAddress, abi: ABI) -> None:
        self._client = client
        self._address = address
        self._abi = abi
        self._contract = self._client.get_contract(address=address, abi=abi)

    @property
    def address(self) -> ChecksumAddress:
        return self._address

    @property
    def abi(self) -> ABI:
        return self._abi

    def _encode_tx(self, fn_name: str, args: list) -> TxParams:
        data = self._contract.encode_abi(
            abi_element_identifier=fn_name,
            args=args,
        )

        return TxParams(
            to=self._contract.address,
            data=data,
        )

    def _extract_event_from_tx(
        self,
        tx_hash: bytes,
        event: ContractEvent,
    ) -> EventData:
        tx_receipt: TxReceipt = self._client._client.eth.get_transaction_receipt(
            HexBytes(tx_hash)
        )
        processed_events = event().process_receipt(
            tx_receipt, EventLogErrorFlags.Discard
        )

        return processed_events[0]
