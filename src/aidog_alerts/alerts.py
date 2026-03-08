from __future__ import annotations

from datetime import datetime, timedelta

from aidog_alerts.models import AlertRule, MarketSample, RuleDecision, RuleDirection, RuleStatus, RuleType
from aidog_alerts.storage import SqliteRepository


WINDOW_TO_DELTA = {
    "5m": timedelta(minutes=5),
    "15m": timedelta(minutes=15),
    "1h": timedelta(hours=1),
    "4h": timedelta(hours=4),
    "24h": timedelta(hours=24),
}


class AlertEngine:
    def __init__(self, repository: SqliteRepository) -> None:
        self.repository = repository

    def evaluate_rule(self, rule: AlertRule, sample: MarketSample) -> RuleDecision:
        if not rule.is_active or rule.status == RuleStatus.DISABLED:
            return RuleDecision(rule_id=rule.id or 0, is_triggered=False, next_status=RuleStatus.DISABLED)

        if rule.rule_type == RuleType.PRICE_BELOW:
            return self._evaluate_price_rule(rule, sample)
        if rule.rule_type == RuleType.CHANGE_PERCENT:
            return self._evaluate_change_rule(rule, sample)
        raise ValueError(f"unsupported rule type: {rule.rule_type}")

    def _evaluate_price_rule(self, rule: AlertRule, sample: MarketSample) -> RuleDecision:
        assert rule.id is not None
        assert rule.target_price_usd is not None
        if sample.price_usd <= rule.target_price_usd:
            if self._is_eligible_to_trigger(rule, sample.sampled_at):
                return RuleDecision(
                    rule_id=rule.id,
                    is_triggered=True,
                    next_status=RuleStatus.TRIGGERED,
                    trigger_reason=f"price <= {rule.target_price_usd:.8f}",
                )
            return RuleDecision(rule_id=rule.id, is_triggered=False, next_status=RuleStatus.COOLING_DOWN)
        return RuleDecision(rule_id=rule.id, is_triggered=False, next_status=RuleStatus.ARMED)

    def _evaluate_change_rule(self, rule: AlertRule, sample: MarketSample) -> RuleDecision:
        assert rule.id is not None
        assert rule.direction is not None
        assert rule.window_code is not None
        assert rule.target_percent is not None

        window = WINDOW_TO_DELTA[rule.window_code]
        tolerance = timedelta(seconds=max(45, int(window.total_seconds() * 0.1)))
        target_time = sample.sampled_at - window
        base_snapshot = self.repository.get_snapshot_before(rule.asset_id, target_time, tolerance)
        if base_snapshot is None:
            return RuleDecision(rule_id=rule.id, is_triggered=False, next_status=RuleStatus.ARMED)

        base_price = float(base_snapshot["price_usd"])
        if base_price <= 0:
            return RuleDecision(rule_id=rule.id, is_triggered=False, next_status=RuleStatus.ARMED)

        change_percent = ((sample.price_usd - base_price) / base_price) * 100
        threshold_crossed = (
            change_percent >= rule.target_percent
            if rule.direction == RuleDirection.UP
            else change_percent <= -rule.target_percent
        )
        if threshold_crossed:
            if self._is_eligible_to_trigger(rule, sample.sampled_at):
                label = "up" if rule.direction == RuleDirection.UP else "down"
                return RuleDecision(
                    rule_id=rule.id,
                    is_triggered=True,
                    next_status=RuleStatus.TRIGGERED,
                    trigger_reason=f"{rule.window_code} {label} move reached {change_percent:.2f}%",
                    base_price_usd=base_price,
                    change_percent=change_percent,
                )
            return RuleDecision(
                rule_id=rule.id,
                is_triggered=False,
                next_status=RuleStatus.COOLING_DOWN,
                base_price_usd=base_price,
                change_percent=change_percent,
            )
        return RuleDecision(
            rule_id=rule.id,
            is_triggered=False,
            next_status=RuleStatus.ARMED,
            base_price_usd=base_price,
            change_percent=change_percent,
        )

    @staticmethod
    def _is_eligible_to_trigger(rule: AlertRule, now: datetime) -> bool:
        if rule.last_triggered_at is None:
            return True
        return now - rule.last_triggered_at >= timedelta(seconds=rule.cooldown_seconds)
