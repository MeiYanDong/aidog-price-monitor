from __future__ import annotations

from dataclasses import dataclass

from aidog_alerts.alerts import AlertEngine
from aidog_alerts.config import AIDOG, AssetConfig, DEFAULT_MIN_LIQUIDITY_USD
from aidog_alerts.dexscreener import DexScreenerClient, sample_to_dict
from aidog_alerts.feishu import FeishuNotifier
from aidog_alerts.models import MarketSample
from aidog_alerts.storage import SqliteRepository


@dataclass(frozen=True, slots=True)
class PollOutcome:
    sample: MarketSample
    asset_id: int
    triggered_rule_ids: list[int]
    notification_statuses: list[str]


class AidogAlertService:
    def __init__(
        self,
        repository: SqliteRepository,
        client: DexScreenerClient,
        notifier: FeishuNotifier,
        asset: AssetConfig = AIDOG,
        min_liquidity_usd: float = DEFAULT_MIN_LIQUIDITY_USD,
    ) -> None:
        self.repository = repository
        self.client = client
        self.notifier = notifier
        self.asset = asset
        self.min_liquidity_usd = min_liquidity_usd
        self.engine = AlertEngine(repository)

    def bootstrap_asset(self) -> int:
        return self.repository.upsert_asset(self.asset)

    def poll_once(self) -> PollOutcome:
        asset_id = self.bootstrap_asset()
        sample = self.client.fetch_pair_sample(self.asset)
        if sample.liquidity_usd < self.min_liquidity_usd:
            raise RuntimeError(
                f"insufficient liquidity for alerts: {sample.liquidity_usd:.2f} < {self.min_liquidity_usd:.2f}"
            )

        self.repository.save_snapshot(asset_id, sample)
        rules = self.repository.list_active_rules(asset_id)
        triggered_rule_ids: list[int] = []
        notification_statuses: list[str] = []
        for rule in rules:
            decision = self.engine.evaluate_rule(rule, sample)
            triggered_at = sample.sampled_at if decision.is_triggered else rule.last_triggered_at
            notified_price = sample.price_usd if decision.is_triggered else rule.last_notified_price_usd
            self.repository.update_rule_state(
                rule_id=rule.id or 0,
                status=decision.next_status,
                last_triggered_at=triggered_at,
                last_notified_price_usd=notified_price,
            )
            if not decision.is_triggered:
                continue
            notification = self.notifier.send_alert(
                asset_name=self.asset.symbol,
                chain_id=self.asset.chain_id,
                pair_address=self.asset.pair_address,
                sample=sample,
                rule=rule,
                trigger_reason=decision.trigger_reason or "threshold reached",
                base_price_usd=decision.base_price_usd,
                change_percent=decision.change_percent,
            )
            self.repository.log_alert_event(
                rule_id=rule.id or 0,
                asset_id=asset_id,
                triggered_price_usd=sample.price_usd,
                base_price_usd=decision.base_price_usd,
                change_percent=decision.change_percent,
                trigger_reason=decision.trigger_reason or "threshold reached",
                notify_status=notification.status,
                notify_response=notification.response,
                triggered_at=sample.sampled_at,
            )
            triggered_rule_ids.append(rule.id or 0)
            notification_statuses.append(notification.status)
        return PollOutcome(
            sample=sample,
            asset_id=asset_id,
            triggered_rule_ids=triggered_rule_ids,
            notification_statuses=notification_statuses,
        )

    def fetch_current_sample(self) -> dict:
        sample = self.client.fetch_pair_sample(self.asset)
        return sample_to_dict(sample)
