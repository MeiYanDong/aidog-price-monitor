from __future__ import annotations

from datetime import datetime, timezone

from aidog_alerts.feishu import build_card_payload
from aidog_alerts.models import AlertRule, MarketSample, RuleDirection, RuleStatus, RuleType


def make_sample() -> MarketSample:
    return MarketSample(
        symbol="AIDOG",
        chain_id="base",
        token_address="0x80394ae69f14444605032a7f2d74c8ab7d16a51d",
        pair_address="0xDaAe8AfdEb4d31e4F6A0cDB9d490D4188d48C0A9",
        dex_id="uniswap",
        quote_symbol="VIRTUAL",
        price_usd=0.00398,
        price_native=0.00565,
        liquidity_usd=500000,
        volume_24h=10000,
        price_change_24h=-1.2,
        sampled_at=datetime(2026, 2, 27, 12, 14, 7, tzinfo=timezone.utc),
        raw_payload="{}",
    )


def test_build_card_payload_for_price_rule() -> None:
    rule = AlertRule(
        id=1,
        asset_id=1,
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

    payload = build_card_payload("AIDOG", make_sample(), rule)

    assert payload["msg_type"] == "interactive"
    assert payload["card"]["header"]["title"]["content"] == "AIDOG 价格提醒"
    fields = payload["card"]["elements"][0]["fields"]
    assert len(fields) == 3
    assert "0.0040 USD" in fields[0]["text"]["content"]
    assert "<=" in fields[1]["text"]["content"]
    assert "0.0040 USD" in fields[1]["text"]["content"]


def test_build_card_payload_for_change_rule() -> None:
    rule = AlertRule(
        id=2,
        asset_id=1,
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

    payload = build_card_payload("AIDOG", make_sample(), rule, change_percent=-5.75)

    assert payload["msg_type"] == "interactive"
    assert payload["card"]["header"]["title"]["content"] == "AIDOG 涨跌幅提醒"
    fields = payload["card"]["elements"][0]["fields"]
    assert len(fields) == 4
    assert "0.0040 USD" in fields[0]["text"]["content"]
    assert "-5.75%" in fields[1]["text"]["content"]
