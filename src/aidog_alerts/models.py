from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum


class RuleType(StrEnum):
    PRICE_BELOW = "price_below"
    CHANGE_PERCENT = "change_percent"


class RuleDirection(StrEnum):
    UP = "up"
    DOWN = "down"


class RuleStatus(StrEnum):
    ENABLED = "enabled"
    ARMED = "armed"
    TRIGGERED = "triggered"
    COOLING_DOWN = "cooling_down"
    DISABLED = "disabled"


@dataclass(slots=True)
class MarketSample:
    symbol: str
    chain_id: str
    token_address: str
    pair_address: str
    dex_id: str
    quote_symbol: str
    price_usd: float
    price_native: float
    liquidity_usd: float
    volume_24h: float
    price_change_24h: float
    sampled_at: datetime
    raw_payload: str


@dataclass(slots=True)
class AlertRule:
    id: int | None
    asset_id: int
    rule_type: RuleType
    direction: RuleDirection | None
    target_price_usd: float | None
    window_code: str | None
    target_percent: float | None
    cooldown_seconds: int
    status: RuleStatus
    last_triggered_at: datetime | None
    last_notified_price_usd: float | None
    is_active: bool


@dataclass(frozen=True, slots=True)
class RuleDecision:
    rule_id: int
    is_triggered: bool
    next_status: RuleStatus
    trigger_reason: str | None = None
    base_price_usd: float | None = None
    change_percent: float | None = None
