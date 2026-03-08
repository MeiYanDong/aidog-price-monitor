from __future__ import annotations

import argparse
import json
import os
import time
from pathlib import Path

from aidog_alerts.config import AIDOG
from aidog_alerts.dexscreener import DexScreenerClient
from aidog_alerts.feishu import FeishuNotifier
from aidog_alerts.models import RuleDirection
from aidog_alerts.service import AidogAlertService
from aidog_alerts.storage import SqliteRepository


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="AIDOG alert prototype CLI")
    parser.add_argument("--db", default="data/aidog_alerts.db", help="sqlite db path")
    parser.add_argument(
        "--webhook-url",
        default=os.getenv("FEISHU_WEBHOOK_URL") or os.getenv("FEISHU_WEBHOOK"),
        help="Feishu webhook URL",
    )
    parser.add_argument("--webhook-secret", default=os.getenv("FEISHU_SECRET"), help="Feishu webhook secret")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("init-db", help="initialize sqlite schema")
    subparsers.add_parser("fetch-current", help="fetch current AIDOG price from DEX Screener")

    create_price = subparsers.add_parser("create-price-rule", help="create price below rule")
    create_price.add_argument("--target-price", type=float, required=True)
    create_price.add_argument("--cooldown", type=int, default=14400)

    poll = subparsers.add_parser("poll-once", help="fetch, store, evaluate and notify once")
    poll.add_argument("--dry-run", action="store_true", help="render Feishu payload without sending")

    run_loop = subparsers.add_parser("run-loop", help="poll continuously on a fixed interval")
    run_loop.add_argument("--interval-seconds", type=int, default=60, help="poll interval in seconds")
    run_loop.add_argument("--max-iterations", type=int, default=0, help="optional limit for loop iterations")
    run_loop.add_argument("--dry-run", action="store_true", help="render Feishu payload without sending")

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    db_path = Path(args.db)
    db_path.parent.mkdir(parents=True, exist_ok=True)

    repository = SqliteRepository(db_path)
    client = DexScreenerClient()
    notifier = FeishuNotifier(
        webhook_url=args.webhook_url,
        secret=args.webhook_secret,
        dry_run=getattr(args, "dry_run", False),
    )
    service = AidogAlertService(repository=repository, client=client, notifier=notifier)

    if args.command == "init-db":
        repository.initialize()
        asset_id = service.bootstrap_asset()
        print(json.dumps({"ok": True, "assetId": asset_id, "symbol": AIDOG.symbol}, ensure_ascii=True))
        return

    if args.command == "fetch-current":
        print(json.dumps(service.fetch_current_sample(), ensure_ascii=True, indent=2))
        return

    repository.initialize()
    asset_id = service.bootstrap_asset()

    if args.command == "create-price-rule":
        rule_id = repository.create_price_rule(
            asset_id=asset_id,
            target_price_usd=args.target_price,
            cooldown_seconds=args.cooldown,
        )
        print(json.dumps({"ok": True, "ruleId": rule_id, "type": "price_below"}, ensure_ascii=True))
        return

    if args.command == "poll-once":
        outcome = service.poll_once()
        print_poll_outcome(outcome)
        return

    if args.command == "run-loop":
        iteration = 0
        while True:
            outcome = service.poll_once()
            print_poll_outcome(outcome)
            iteration += 1
            if args.max_iterations and iteration >= args.max_iterations:
                return
            time.sleep(args.interval_seconds)

    parser.error(f"unsupported command: {args.command}")


def print_poll_outcome(outcome) -> None:
    print(
        json.dumps(
            {
                "ok": True,
                "assetId": outcome.asset_id,
                "priceUsd": outcome.sample.price_usd,
                "liquidityUsd": outcome.sample.liquidity_usd,
                "triggeredRuleIds": outcome.triggered_rule_ids,
                "notificationStatuses": outcome.notification_statuses,
            },
            ensure_ascii=True,
            indent=2,
        ),
        flush=True,
    )


if __name__ == "__main__":
    main()
