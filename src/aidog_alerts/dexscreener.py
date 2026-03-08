from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime, timezone
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from aidog_alerts.config import AssetConfig
from aidog_alerts.models import MarketSample


class DexScreenerError(RuntimeError):
    """Raised when DEX Screener data cannot be loaded or validated."""


HttpGet = Callable[[str], dict[str, Any] | list[dict[str, Any]]]


def default_http_get(url: str) -> dict[str, Any] | list[dict[str, Any]]:
    request = Request(url, headers={"User-Agent": "aidog-alerts/0.1"})
    try:
        with urlopen(request, timeout=10) as response:
            return json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError, TimeoutError) as exc:
        raise DexScreenerError(f"failed to fetch DEX Screener url={url}: {exc}") from exc


class DexScreenerClient:
    def __init__(self, http_get: HttpGet | None = None) -> None:
        self._http_get = http_get or default_http_get

    def fetch_token_pairs(self, asset: AssetConfig) -> list[dict[str, Any]]:
        url = (
            "https://api.dexscreener.com/token-pairs/v1/"
            f"{asset.chain_id}/{asset.token_address}"
        )
        payload = self._http_get(url)
        if not isinstance(payload, list):
            raise DexScreenerError("token-pairs response must be a list")
        return payload

    def fetch_pair_sample(self, asset: AssetConfig) -> MarketSample:
        url = (
            "https://api.dexscreener.com/latest/dex/pairs/"
            f"{asset.chain_id}/{asset.pair_address}"
        )
        payload = self._http_get(url)
        if not isinstance(payload, dict):
            raise DexScreenerError("pair response must be a dict")
        pair = self._extract_pair(payload, asset)
        try:
            return MarketSample(
                symbol=pair["baseToken"]["symbol"],
                chain_id=pair["chainId"],
                token_address=pair["baseToken"]["address"],
                pair_address=pair["pairAddress"],
                dex_id=pair["dexId"],
                quote_symbol=pair["quoteToken"]["symbol"],
                price_usd=float(pair["priceUsd"]),
                price_native=float(pair["priceNative"]),
                liquidity_usd=float(pair["liquidity"]["usd"]),
                volume_24h=float(pair["volume"]["h24"]),
                price_change_24h=float(pair["priceChange"]["h24"]),
                sampled_at=datetime.now(timezone.utc),
                raw_payload=json.dumps(pair, ensure_ascii=True, sort_keys=True),
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise DexScreenerError(f"invalid pair payload: {exc}") from exc

    def _extract_pair(self, payload: dict[str, Any], asset: AssetConfig) -> dict[str, Any]:
        pair = payload.get("pair")
        if pair:
            self._validate_pair_identity(pair, asset)
            return pair

        pairs = payload.get("pairs")
        if not isinstance(pairs, list) or not pairs:
            raise DexScreenerError("pairs response is empty")

        for candidate in pairs:
            if candidate.get("pairAddress", "").lower() == asset.pair_address.lower():
                self._validate_pair_identity(candidate, asset)
                return candidate

        raise DexScreenerError("configured pair was not found in pairs response")

    @staticmethod
    def _validate_pair_identity(pair: dict[str, Any], asset: AssetConfig) -> None:
        if pair.get("chainId") != asset.chain_id:
            raise DexScreenerError("pair chain mismatch")
        if pair.get("pairAddress", "").lower() != asset.pair_address.lower():
            raise DexScreenerError("pair address mismatch")
        base_token = pair.get("baseToken", {})
        if base_token.get("address", "").lower() != asset.token_address.lower():
            raise DexScreenerError("token address mismatch")


def sample_to_dict(sample: MarketSample) -> dict[str, Any]:
    data = asdict(sample)
    data["sampled_at"] = sample.sampled_at.isoformat()
    return data
