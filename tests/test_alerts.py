from __future__ import annotations

from datetime import datetime, timedelta, timezone

from aidog_alerts.alerts import AlertEngine
from aidog_alerts.config import AIDOG
from aidog_alerts.models import AlertRule, MarketSample, RuleDirection, RuleStatus, RuleType
from aidog_alerts.storage import SqliteRepository


def make_sample(price: float, sampled_at: datetime) -> MarketSample:
    return MarketSample(
        symbol="AIDOG",
        chain_id="base",
        token_address=AIDOG.token_address,
        pair_address=AIDOG.pair_address,
        dex_id="uniswap",
        quote_symbol="VIRTUAL",
        price_usd=price,
        price_native=price * 1.42,
        liquidity_usd=200000.0,
        volume_24h=5000.0,
        price_change_24h=-2.5,
        sampled_at=sampled_at,
        raw_payload="{}",
    )


def test_price_rule_triggers_when_threshold_crossed(tmp_path) -> None:
    repository = SqliteRepository(tmp_path / "alerts.db")
    repository.initialize()
    asset_id = repository.upsert_asset(AIDOG)
    rule = AlertRule(
        id=1,
        asset_id=asset_id,
        rule_type=RuleType.PRICE_BELOW,
        direction=None,
        target_price_usd=0.004,
        window_code=None,
        target_percent=None,
        cooldown_seconds=1800,
        status=RuleStatus.ARMED,
        last_triggered_at=None,
        last_notified_price_usd=None,
        is_active=True,
    )

    decision = AlertEngine(repository).evaluate_rule(
        rule,
        make_sample(0.0039, datetime.now(timezone.utc)),
    )

    assert decision.is_triggered is True
    assert decision.next_status == RuleStatus.TRIGGERED


def test_change_rule_uses_snapshot_window(tmp_path) -> None:
    repository = SqliteRepository(tmp_path / "alerts.db")
    repository.initialize()
    asset_id = repository.upsert_asset(AIDOG)

    now = datetime(2026, 2, 27, 12, 0, tzinfo=timezone.utc)
    repository.save_snapshot(asset_id, make_sample(0.0050, now - timedelta(minutes=15, seconds=10)))
    rule = AlertRule(
        id=2,
        asset_id=asset_id,
        rule_type=RuleType.CHANGE_PERCENT,
        direction=RuleDirection.DOWN,
        target_price_usd=None,
        window_code="15m",
        target_percent=5.0,
        cooldown_seconds=1800,
        status=RuleStatus.ARMED,
        last_triggered_at=None,
        last_notified_price_usd=None,
        is_active=True,
    )

    decision = AlertEngine(repository).evaluate_rule(rule, make_sample(0.0047, now))

    assert decision.is_triggered is True
    assert decision.base_price_usd == 0.0050
    assert round(decision.change_percent or 0.0, 2) == -6.00
