from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class AssetConfig:
    symbol: str
    chain_id: str
    token_address: str
    pair_address: str
    dex_id: str
    quote_symbol: str


AIDOG = AssetConfig(
    symbol="AIDOG",
    chain_id="base",
    token_address="0x80394ae69f14444605032a7f2d74c8ab7d16a51d",
    pair_address="0xDaAe8AfdEb4d31e4F6A0cDB9d490D4188d48C0A9",
    dex_id="uniswap",
    quote_symbol="VIRTUAL",
)

DEFAULT_SNAPSHOT_INTERVAL_SECONDS = 30
DEFAULT_MIN_LIQUIDITY_USD = 10_000.0
