from __future__ import annotations

import json
import sqlite3
from contextlib import closing
from datetime import datetime, timedelta, timezone
from pathlib import Path

from aidog_alerts.config import AssetConfig
from aidog_alerts.models import AlertRule, MarketSample, RuleDirection, RuleStatus, RuleType


class SqliteRepository:
    def __init__(self, db_path: str | Path) -> None:
        self.db_path = str(db_path)

    def connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def initialize(self) -> None:
        with closing(self.connect()) as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS tracked_assets (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    chain_id TEXT NOT NULL,
                    token_address TEXT NOT NULL,
                    pair_address TEXT NOT NULL,
                    dex_id TEXT NOT NULL,
                    quote_symbol TEXT NOT NULL,
                    is_active INTEGER NOT NULL DEFAULT 1,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE UNIQUE INDEX IF NOT EXISTS idx_tracked_assets_unique
                ON tracked_assets(chain_id, token_address, pair_address);

                CREATE TABLE IF NOT EXISTS price_snapshots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    asset_id INTEGER NOT NULL,
                    pair_address TEXT NOT NULL,
                    price_usd REAL NOT NULL,
                    price_native REAL NOT NULL,
                    liquidity_usd REAL NOT NULL,
                    volume_24h REAL NOT NULL,
                    price_change_24h REAL NOT NULL,
                    sampled_at TEXT NOT NULL,
                    raw_payload TEXT NOT NULL,
                    FOREIGN KEY (asset_id) REFERENCES tracked_assets(id)
                );

                CREATE INDEX IF NOT EXISTS idx_price_snapshots_asset_sampled_at
                ON price_snapshots(asset_id, sampled_at DESC);

                CREATE TABLE IF NOT EXISTS alert_rules (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    asset_id INTEGER NOT NULL,
                    rule_type TEXT NOT NULL,
                    direction TEXT,
                    target_price_usd REAL,
                    window_code TEXT,
                    target_percent REAL,
                    cooldown_seconds INTEGER NOT NULL,
                    status TEXT NOT NULL,
                    last_triggered_at TEXT,
                    last_notified_price_usd REAL,
                    is_active INTEGER NOT NULL DEFAULT 1,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY (asset_id) REFERENCES tracked_assets(id)
                );

                CREATE TABLE IF NOT EXISTS alert_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    rule_id INTEGER NOT NULL,
                    asset_id INTEGER NOT NULL,
                    triggered_price_usd REAL NOT NULL,
                    base_price_usd REAL,
                    change_percent REAL,
                    trigger_reason TEXT NOT NULL,
                    notify_status TEXT NOT NULL,
                    notify_response TEXT NOT NULL,
                    triggered_at TEXT NOT NULL,
                    FOREIGN KEY (rule_id) REFERENCES alert_rules(id),
                    FOREIGN KEY (asset_id) REFERENCES tracked_assets(id)
                );
                """
            )
            conn.commit()

    def upsert_asset(self, asset: AssetConfig) -> int:
        now = utc_now().isoformat()
        with closing(self.connect()) as conn:
            row = conn.execute(
                """
                SELECT id FROM tracked_assets
                WHERE chain_id = ? AND token_address = ? AND pair_address = ?
                """,
                (asset.chain_id, asset.token_address.lower(), asset.pair_address.lower()),
            ).fetchone()
            if row:
                conn.execute(
                    """
                    UPDATE tracked_assets
                    SET symbol = ?, dex_id = ?, quote_symbol = ?, is_active = 1, updated_at = ?
                    WHERE id = ?
                    """,
                    (asset.symbol, asset.dex_id, asset.quote_symbol, now, row["id"]),
                )
                conn.commit()
                return int(row["id"])

            cursor = conn.execute(
                """
                INSERT INTO tracked_assets (
                    symbol, chain_id, token_address, pair_address, dex_id, quote_symbol,
                    is_active, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, 1, ?, ?)
                """,
                (
                    asset.symbol,
                    asset.chain_id,
                    asset.token_address.lower(),
                    asset.pair_address.lower(),
                    asset.dex_id,
                    asset.quote_symbol,
                    now,
                    now,
                ),
            )
            conn.commit()
            return int(cursor.lastrowid)

    def save_snapshot(self, asset_id: int, sample: MarketSample) -> int:
        with closing(self.connect()) as conn:
            cursor = conn.execute(
                """
                INSERT INTO price_snapshots (
                    asset_id, pair_address, price_usd, price_native, liquidity_usd,
                    volume_24h, price_change_24h, sampled_at, raw_payload
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    asset_id,
                    sample.pair_address.lower(),
                    sample.price_usd,
                    sample.price_native,
                    sample.liquidity_usd,
                    sample.volume_24h,
                    sample.price_change_24h,
                    sample.sampled_at.isoformat(),
                    sample.raw_payload,
                ),
            )
            conn.commit()
            return int(cursor.lastrowid)

    def create_price_rule(
        self,
        asset_id: int,
        target_price_usd: float,
        cooldown_seconds: int = 14400,
    ) -> int:
        return self._create_rule(
            asset_id=asset_id,
            rule_type=RuleType.PRICE_BELOW,
            direction=None,
            target_price_usd=target_price_usd,
            window_code=None,
            target_percent=None,
            cooldown_seconds=cooldown_seconds,
        )

    def create_change_rule(
        self,
        asset_id: int,
        direction: RuleDirection,
        window_code: str,
        target_percent: float,
        cooldown_seconds: int = 1800,
    ) -> int:
        return self._create_rule(
            asset_id=asset_id,
            rule_type=RuleType.CHANGE_PERCENT,
            direction=direction,
            target_price_usd=None,
            window_code=window_code,
            target_percent=target_percent,
            cooldown_seconds=cooldown_seconds,
        )

    def _create_rule(
        self,
        asset_id: int,
        rule_type: RuleType,
        direction: RuleDirection | None,
        target_price_usd: float | None,
        window_code: str | None,
        target_percent: float | None,
        cooldown_seconds: int,
    ) -> int:
        now = utc_now().isoformat()
        with closing(self.connect()) as conn:
            cursor = conn.execute(
                """
                INSERT INTO alert_rules (
                    asset_id, rule_type, direction, target_price_usd, window_code,
                    target_percent, cooldown_seconds, status, is_active, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?)
                """,
                (
                    asset_id,
                    rule_type.value,
                    direction.value if direction else None,
                    target_price_usd,
                    window_code,
                    target_percent,
                    cooldown_seconds,
                    RuleStatus.ARMED.value,
                    now,
                    now,
                ),
            )
            conn.commit()
            return int(cursor.lastrowid)

    def list_active_rules(self, asset_id: int) -> list[AlertRule]:
        with closing(self.connect()) as conn:
            rows = conn.execute(
                """
                SELECT * FROM alert_rules
                WHERE asset_id = ? AND is_active = 1 AND rule_type = ?
                ORDER BY id ASC
                """,
                (asset_id, RuleType.PRICE_BELOW.value),
            ).fetchall()
        return [self._row_to_rule(row) for row in rows]

    def get_latest_snapshot(self, asset_id: int) -> sqlite3.Row | None:
        with closing(self.connect()) as conn:
            return conn.execute(
                """
                SELECT * FROM price_snapshots
                WHERE asset_id = ?
                ORDER BY sampled_at DESC
                LIMIT 1
                """,
                (asset_id,),
            ).fetchone()

    def get_snapshot_before(
        self,
        asset_id: int,
        target_time: datetime,
        tolerance: timedelta,
    ) -> sqlite3.Row | None:
        with closing(self.connect()) as conn:
            row = conn.execute(
                """
                SELECT * FROM price_snapshots
                WHERE asset_id = ? AND sampled_at <= ?
                ORDER BY sampled_at DESC
                LIMIT 1
                """,
                (asset_id, target_time.isoformat()),
            ).fetchone()
        if row is None:
            return None
        sampled_at = parse_dt(row["sampled_at"])
        if target_time - sampled_at > tolerance:
            return None
        return row

    def update_rule_state(
        self,
        rule_id: int,
        status: RuleStatus,
        last_triggered_at: datetime | None,
        last_notified_price_usd: float | None,
    ) -> None:
        with closing(self.connect()) as conn:
            conn.execute(
                """
                UPDATE alert_rules
                SET status = ?, last_triggered_at = ?, last_notified_price_usd = ?, updated_at = ?
                WHERE id = ?
                """,
                (
                    status.value,
                    last_triggered_at.isoformat() if last_triggered_at else None,
                    last_notified_price_usd,
                    utc_now().isoformat(),
                    rule_id,
                ),
            )
            conn.commit()

    def log_alert_event(
        self,
        rule_id: int,
        asset_id: int,
        triggered_price_usd: float,
        base_price_usd: float | None,
        change_percent: float | None,
        trigger_reason: str,
        notify_status: str,
        notify_response: dict,
        triggered_at: datetime,
    ) -> int:
        with closing(self.connect()) as conn:
            cursor = conn.execute(
                """
                INSERT INTO alert_events (
                    rule_id, asset_id, triggered_price_usd, base_price_usd, change_percent,
                    trigger_reason, notify_status, notify_response, triggered_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    rule_id,
                    asset_id,
                    triggered_price_usd,
                    base_price_usd,
                    change_percent,
                    trigger_reason,
                    notify_status,
                    json.dumps(notify_response, ensure_ascii=True, sort_keys=True),
                    triggered_at.isoformat(),
                ),
            )
            conn.commit()
            return int(cursor.lastrowid)

    @staticmethod
    def _row_to_rule(row: sqlite3.Row) -> AlertRule:
        return AlertRule(
            id=int(row["id"]),
            asset_id=int(row["asset_id"]),
            rule_type=RuleType(row["rule_type"]),
            direction=RuleDirection(row["direction"]) if row["direction"] else None,
            target_price_usd=row["target_price_usd"],
            window_code=row["window_code"],
            target_percent=row["target_percent"],
            cooldown_seconds=int(row["cooldown_seconds"]),
            status=RuleStatus(row["status"]),
            last_triggered_at=parse_dt(row["last_triggered_at"]) if row["last_triggered_at"] else None,
            last_notified_price_usd=row["last_notified_price_usd"],
            is_active=bool(row["is_active"]),
        )


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def parse_dt(value: str) -> datetime:
    return datetime.fromisoformat(value)
