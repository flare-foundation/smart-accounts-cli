import json

from web3 import exceptions

from clients import FlareSigningClient
from clients.singleton import clients as c
from configuration.settings import settings
from src.cli.types import CustomRegister


def custom_register(args: CustomRegister):
    mac = c.master_account_controller
    f = FlareSigningClient.default_with_pk(settings.flr_private_key)

    data = json.loads(args.custom_instruction)

    encoded = mac.encode_custom_instruction(data)

    try:
        tx = mac.register_custom_instruction(data)
        f.send_transaction(tx)
    except exceptions.ContractCustomError:
        pass

    print(encoded[2:].hex())
