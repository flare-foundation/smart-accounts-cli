from enum import IntEnum

import attrs
from eth_typing import ChecksumAddress


class AgentStatus(IntEnum):
    NORMAL = 0
    LIQUIDATION = 1
    FULL_LIQUIDATION = 2
    DESTROYING = 3


@attrs.frozen
class AgentInfo:
    status: AgentStatus
    owner_management_address: ChecksumAddress
    owner_work_address: ChecksumAddress
    collateral_pool: ChecksumAddress
    collateral_pool_token: ChecksumAddress
    underlying_address_string: str
    publicly_available: bool
    fee_bips: int
    pool_fee_share_bips: int
    vault_collateral_token: ChecksumAddress
    minting_vault_collateral_ratio_bips: int
    minting_pool_collateral_ratio_bips: int
    free_collateral_lots: int
    total_vault_collateral_wei: int
    free_vault_collateral_wei: int
    vault_collateral_ratio_bips: int
    pool_wnat_token: ChecksumAddress
    total_pool_collateral_nat_wei: int
    free_pool_collateral_nat_wei: int
    pool_collateral_ratio_bips: int
    total_agent_pool_tokens_wei: int
    announced_vault_collateral_withdrawal_wei: int
    announced_pool_tokens_withdrawal_wei: int
    free_agent_pool_tokens_wei: int
    minted_uba: int
    reserved_uba: int
    redeeming_uba: int
    pool_redeeming_uba: int
    dust_uba: int
    liquidation_start_timestamp: int
    max_liquidation_amount_uba: int
    liquidation_payment_factor_vault_bips: int
    liquidation_payment_factor_pool_bips: int
    underlying_balance_uba: int
    required_underlying_balance_uba: int
    free_underlying_balance_uba: int
    announced_underlying_withdrawal_id: int
    buy_fasset_by_agent_factor_bips: int
    pool_exit_collateral_ratio_bips: int
    redemption_pool_fee_share_bips: int


@attrs.frozen
class AssetManagerSettings:
    asset_manager_controller: ChecksumAddress
    fasset: ChecksumAddress
    agent_vault_factory: ChecksumAddress
    collateral_pool_factory: ChecksumAddress
    collateral_pool_token_factory: ChecksumAddress
    pool_token_suffix: ChecksumAddress
    whitelist: ChecksumAddress
    agent_owner_registry: ChecksumAddress
    fdc_verification: ChecksumAddress
    burn_address: ChecksumAddress
    price_reader: ChecksumAddress
    asset_decimals: int
    asset_minting_decimals: int
    chain_id: bytes
    average_block_time_ms: int
    minting_pool_holdings_required_bips: int
    collateral_reservation_fee_bips: int
    asset_unit_uba: int
    asset_minting_granularity_uba: int
    lot_size_amg: int
    min_underlying_backing_bips: int
    require_eoa_address_proof: bool
    minting_cap_amg: int
    underlying_blocks_for_payment: int
    underlying_seconds_for_payment: int
    redemption_fee_bips: int
    redemption_default_factor_vault_collateral_bips: int
    redemption_default_factor_pool_bips: int
    confirmation_by_others_after_seconds: int
    confirmation_by_others_reward_usd5: int
    max_redeemed_tickets: int
    payment_challenge_reward_bips: int
    payment_challenge_reward_usd5: int
    withdrawal_wait_min_seconds: int
    max_trusted_price_age_seconds: int
    ccb_time_seconds: int
    attestation_window_seconds: int
    min_update_repeat_time_seconds: int
    buyback_collateral_factor_bips: int
    announced_underlying_confirmation_min_seconds: int
    token_invalidation_time_min_seconds: int
    vault_collateral_buy_for_flare_factor_bips: int
    agent_exit_available_timelock_seconds: int
    agent_fee_change_timelock_seconds: int
    agent_minting_cr_change_timelock_seconds: int
    pool_exit_cr_change_timelock_seconds: int
    agent_timelocked_operation_window_seconds: int
    collateral_pool_token_timelock_seconds: int
    liquidation_step_seconds: int
    liquidation_collateral_factor_bips: list[int]
    liquidation_factor_vault_collateral_bips: list[int]
    diamond_cut_min_timelock_seconds: int
    max_emergency_pause_duration_seconds: int
    emergency_pause_duration_reset_after_seconds: int
    cancel_collateral_reservation_after_seconds: int
    reject_or_cancel_collateral_reservation_return_factor_bips: int
    reject_redemption_request_window_seconds: int
    take_over_redemption_request_window_seconds: int
    rejected_redemption_default_factor_vault_collateral_bips: int
    rejected_redemption_default_factor_pool_bips: int
