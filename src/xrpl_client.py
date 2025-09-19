from xrpl.account import get_next_valid_seq_number
from xrpl.ledger import get_latest_validated_ledger_sequence
from xrpl.models import Memo, Payment, Response, Tx
from xrpl.transaction import sign, submit_and_wait
from xrpl.wallet import Wallet

from src.registry import registry
from src.settings import settings


def get_tx(tx_hash: str) -> Response:
    return settings.xrpl.request(Tx(transaction=tx_hash))


def get_wallet(secret: str | None = None) -> Wallet:
    if secret is None:
        secret = settings.env.xrpl_seed

    return Wallet.from_seed(secret)


def send_tx(
    amount: str | int,
    destination: str,
    memos: str | list[str] | None,
    last_ledger_sequence: int | None = None,
) -> Response:
    client = settings.xrpl

    if last_ledger_sequence is None:
        last_ledger_sequence = get_latest_validated_ledger_sequence(client) + 20

    wallet = get_wallet()

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
        sequence=get_next_valid_seq_number(wallet.address, client),
        fee="10",
    )

    payment_response = submit_and_wait(sign(payment_tx, wallet), client)
    return get_tx(payment_response.result["hash"])


def send_bridge_request_tx(memo: str) -> Response:
    client = settings.w3

    operator_underlying_address = (
        client.eth.contract(
            address=registry.master_account_controller.address,
            abi=registry.master_account_controller.abi,
        )
        .functions.xrplProviderWallet()
        .call()
    )

    return send_tx(1, operator_underlying_address, memo)
