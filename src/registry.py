import json

from attrs import field, frozen
from eth_typing import ABI, ABIEvent, ABIFunction, ChecksumAddress
from eth_utils.address import to_checksum_address
from web3 import Web3


def abi_from_file_location(file_location: str):
    return json.load(open(file_location))["abi"]


def event_signature(event_abi: ABIEvent) -> str:
    assert "inputs" in event_abi
    params = ""
    for index, input in enumerate(event_abi["inputs"]):
        if index > 0:
            params += ","

        if input["type"] == "tuple[]":
            params += "("
            assert "components" in input
            for index2, tuple_component in enumerate(input["components"]):
                if index2 > 0:
                    params += ","

                params += tuple_component["type"]

            params += ")[]"

        elif input["type"] == "tuple":
            params += "("
            assert "components" in input
            for index2, tuple_component in enumerate(input["components"]):
                if index2 > 0:
                    params += ","

                params += tuple_component["type"]

            params += ")"

        else:
            params += input["type"]

    return Web3.keccak(text=event_abi["name"] + "(" + params + ")").hex()


def function_signature(function_name: str) -> str:
    return Web3.keccak(text=function_name).hex()[:8]


@frozen
class Event:
    name: str
    abi: ABIEvent
    contract: "Contract"
    signature: str = field(init=False)

    def __attrs_post_init__(self):
        object.__setattr__(self, "signature", event_signature(self.abi))


@frozen
class Function:
    name: str
    abi: ABIFunction
    contract: "Contract"
    signature: str = field(init=False)

    def to_full_name(self):
        assert "inputs" in self.abi
        inputs = [i["type"] for i in self.abi["inputs"]]
        return f"{self.name}({','.join(inputs)})"

    def __attrs_post_init__(self):
        object.__setattr__(self, "signature", function_signature(self.to_full_name()))


@frozen
class Contract:
    name: str
    address: ChecksumAddress
    abi: ABI = field(converter=abi_from_file_location)
    events: dict[str, Event] = field(init=False)
    functions: dict[str, Function] = field(init=False)

    def __attrs_post_init__(self):
        events = {}
        functions = {}
        for entry in self.abi:
            assert "type" in entry
            if entry["type"] == "event":
                assert "name" in entry
                events[entry["name"]] = Event(entry["name"], entry, self)
            elif entry["type"] == "function":
                assert "name" in entry
                functions[entry["name"]] = Function(entry["name"], entry, self)
        object.__setattr__(self, "events", events)
        object.__setattr__(self, "functions", functions)


class Registry:
    master_account_controller = Contract(
        name="MasterAccountController",
        address=to_checksum_address("0xa7bc2aC84DB618fde9fa4892D1166fFf75D36FA6"),
        abi="./abis/MasterAccountController.json",
    )

    master_account_controller_dev_mock = Contract(
        name="MasterAccountControllerDevMock",
        address=to_checksum_address("0x787419810116b29fbB45a7E679Ae6c3dfCA9600b"),
        abi="./abis/MasterAccountControllerDevMock.json",
    )

    asset_manager_events = Contract(
        name="AssetManagerFXRP",
        address=to_checksum_address("0xc1Ca88b937d0b528842F95d5731ffB586f4fbDFA"),
        abi="./abis/IAssetManagerEvents.json",
    )


registry = Registry
