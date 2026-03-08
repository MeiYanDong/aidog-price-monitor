# AIDOG Price Monitor

A lightweight AIDOG price monitor that polls DEX Screener, stores price snapshots in SQLite, and sends Feishu alerts when the price drops below a configured threshold.

## Current behavior

- Asset: `AIDOG` on `Base`
- Price source: DEX Screener
- Alert type: price-below only
- Poll interval: `60s`
- Cooldown: `4h`
- Notification channel: Feishu bot webhook

## Local usage

```powershell
python main.py --db data\aidog_monitor.db init-db
python main.py --db data\aidog_monitor.db fetch-current
python main.py --db data\aidog_monitor.db create-price-rule --target-price 0.004
python main.py --db data\aidog_monitor.db run-loop --interval-seconds 60
```

## Tests

```powershell
pytest -q tests\test_cli.py tests\test_dexscreener.py tests\test_feishu.py
```

## Deployment

The project is currently deployed on a cloud server as a `systemd` service:

- Service: `aidog-price-monitor.service`
- Project dir: `/root/aidog-price-monitor`
