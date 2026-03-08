from __future__ import annotations

from aidog_alerts.config import AIDOG
from aidog_alerts.dexscreener import DexScreenerClient
from aidog_alerts.feishu import FeishuNotifier
from aidog_alerts.service import AidogAlertService
from aidog_alerts.storage import SqliteRepository


def test_service_polls_and_logs_alert_event(tmp_path) -> None:
    repository = SqliteRepository(tmp_path / "alerts.db")
    repository.initialize()
    notifier = FeishuNotifier(webhook_url=None, dry_run=True)
    client = DexScreenerClient(
        http_get=lambda _url: {
            "pair": {
                "chainId": "base",
                "dexId": "uniswap",
                "pairAddress": AIDOG.pair_address,
                "baseToken": {"address": AIDOG.token_address, "symbol": "AIDOG"},
                "quoteToken": {"symbol": "VIRTUAL"},
                "priceUsd": "0.0039",
                "priceNative": "0.0055",
                "liquidity": {"usd": 500000},
                "volume": {"h24": 10000},
                "priceChange": {"h24": -1.2},
            }
        }
    )
    service = AidogAlertService(repository=repository, client=client, notifier=notifier)
    asset_id = service.bootstrap_asset()
    repository.create_price_rule(asset_id=asset_id, target_price_usd=0.0040)

    outcome = service.poll_once()

    assert outcome.triggered_rule_ids == [1]
    assert outcome.notification_statuses == ["dry_run"]
    latest_snapshot = repository.get_latest_snapshot(asset_id)
    assert latest_snapshot is not None
    assert latest_snapshot["price_usd"] == 0.0039
