from __future__ import annotations

from aidog_alerts.cli import build_parser


def test_run_loop_parser_accepts_interval() -> None:
    parser = build_parser()

    args = parser.parse_args(
        [
            "--db",
            "data/monitor.db",
            "run-loop",
            "--interval-seconds",
            "60",
            "--max-iterations",
            "1",
        ]
    )

    assert args.command == "run-loop"
    assert args.interval_seconds == 60
    assert args.max_iterations == 1


def test_create_price_rule_default_cooldown_is_14400_seconds() -> None:
    parser = build_parser()

    args = parser.parse_args(
        [
            "create-price-rule",
            "--target-price",
            "0.004",
        ]
    )

    assert args.command == "create-price-rule"
    assert args.cooldown == 14400
