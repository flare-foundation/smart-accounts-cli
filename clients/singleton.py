from typing import Self

import attrs

import clients as c
import configuration.utils


@attrs.frozen
class ClientsSingleton:
    # web3
    flare: c.FlareClient
    xrpl: c.XrplClient

    # smart contracts
    asset_manager: c.AssetManagerClient
    ftso_v2: c.FtsoV2Client
    fxrp: c.FxrpClient
    flare_contract_registry: c.FlareContractRegistryClient
    master_account_controller: c.MasterAccountControllerClient
    wnat: c.WNatClient

    @classmethod
    def default(cls) -> Self:
        flare = c.FlareClient.default()
        xrpl = c.XrplClient.default()

        asset_manager = c.AssetManagerClient.default()
        fxrp = asset_manager.get_fxrp_client()
        ftso_v2 = c.FtsoV2Client.default()
        flare_contract_registry = c.FlareContractRegistryClient.default()
        master_account_controller = c.MasterAccountControllerClient.default()
        wnat = c.WNatClient.default()

        return cls(
            flare=flare,
            xrpl=xrpl,
            asset_manager=asset_manager,
            ftso_v2=ftso_v2,
            fxrp=fxrp,
            flare_contract_registry=flare_contract_registry,
            master_account_controller=master_account_controller,
            wnat=wnat,
        )


clients = configuration.utils.wrap_singleton(ClientsSingleton.default)

__all__ = ["clients"]
