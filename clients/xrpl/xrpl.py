from typing import Self

from xrpl.account import get_next_valid_seq_number
from xrpl.clients import JsonRpcClient
from xrpl.ledger import get_latest_validated_ledger_sequence
from xrpl.models import Memo, Payment, Response, Tx
from xrpl.models.requests import AccountInfo
from xrpl.transaction import sign, submit_and_wait
from xrpl.wallet import Wallet

from configuration.settings import settings


class Client:
    def __init__(self, rpc_url) -> None:
        self.client = JsonRpcClient(rpc_url)

    @classmethod
    def default(cls) -> Self:
        return cls(settings.xrpl_rpc_url)

    def get_balance(self, xrpl_address: str) -> int:
        response = self.client.request(AccountInfo(account=xrpl_address))
        return int(response.result["account_data"]["Balance"])

    def get_tx(self, tx_hash: str) -> Response:
        return self.client.request(Tx(transaction=tx_hash))

    def _get_wallet(self) -> Wallet:
        return Wallet.from_seed(seed=settings.xrpl_seed)

    def send_tx(
        self,
        amount: str | int,
        fee: str | int,
        destination: str,
        memos: str | list[str] | None,
        last_ledger_sequence: int | None = None,
    ) -> Response:
        if last_ledger_sequence is None:
            last_ledger_sequence = (
                get_latest_validated_ledger_sequence(self.client) + 20
            )

        wallet = self._get_wallet()

        built_memos = None

        if isinstance(memos, str):
            built_memos = [Memo(memo_data=memos)]
        elif memos is not None:
            built_memos = [Memo(memo_data=m) for m in memos]

        payment_tx = Payment(
            account=wallet.address,
            amount=str(amount),
            destination=destination,
            memos=built_memos,
            last_ledger_sequence=last_ledger_sequence,
            sequence=get_next_valid_seq_number(wallet.address, self.client),
            fee=str(fee),
        )

        payment_response = submit_and_wait(sign(payment_tx, wallet), self.client)
        return self.get_tx(payment_response.result["hash"])
