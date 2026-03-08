from __future__ import annotations

from aidog_alerts.config import AIDOG
from aidog_alerts.dexscreener import DexScreenerClient


PAIR_PAYLOAD = {
    "pairs": [
        {
            "chainId": "base",
            "dexId": "uniswap",
            "pairAddress": "0xDaAe8AfdEb4d31e4F6A0cDB9d490D4188d48C0A9",
            "baseToken": {
                "address": "0x80394Ae69F14444605032a7f2D74c8AB7d16A51d",
                "symbol": "AIDOG",
            },
            "quoteToken": {"symbol": "VIRTUAL"},
            "priceUsd": "0.004400",
            "priceNative": "0.006255",
            "liquidity": {"usd": 631552.68},
            "volume": {"h24": 16021.31},
            "priceChange": {"h24": -5.91},
        }
    ]
}


def test_fetch_pair_sample_normalizes_payload() -> None:
    client = DexScreenerClient(http_get=lambda _url: PAIR_PAYLOAD)

    sample = client.fetch_pair_sample(AIDOG)

    assert sample.symbol == "AIDOG"
    assert sample.chain_id == "base"
    assert sample.token_address.lower() == AIDOG.token_address.lower()
    assert sample.pair_address.lower() == AIDOG.pair_address.lower()
    assert sample.price_usd == 0.0044
    assert sample.liquidity_usd == 631552.68
