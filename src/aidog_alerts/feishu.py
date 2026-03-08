from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from dataclasses import dataclass
from datetime import timezone
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from aidog_alerts.models import AlertRule, MarketSample, RuleDirection, RuleType


JsonPost = Callable[[str, dict[str, Any], dict[str, str]], dict[str, Any]]


@dataclass(frozen=True, slots=True)
class NotificationResult:
    status: str
    response: dict[str, Any]


def default_json_post(url: str, payload: dict[str, Any], headers: dict[str, str]) -> dict[str, Any]:
    request = Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", **headers},
        method="POST",
    )
    try:
        with urlopen(request, timeout=10) as response:
            body = response.read().decode("utf-8")
            return json.loads(body) if body else {"ok": True}
    except (HTTPError, URLError, TimeoutError) as exc:
        return {"ok": False, "error": str(exc)}


class FeishuNotifier:
    def __init__(
        self,
        webhook_url: str | None,
        secret: str | None = None,
        dry_run: bool = False,
        json_post: JsonPost | None = None,
    ) -> None:
        self.webhook_url = webhook_url
        self.secret = secret
        self.dry_run = dry_run
        self._json_post = json_post or default_json_post

    def send_alert(
        self,
        asset_name: str,
        chain_id: str,
        pair_address: str,
        sample: MarketSample,
        rule: AlertRule,
        trigger_reason: str,
        base_price_usd: float | None = None,
        change_percent: float | None = None,
    ) -> NotificationResult:
        payload = build_card_payload(
            asset_name=asset_name,
            sample=sample,
            rule=rule,
            change_percent=change_percent,
        )
        if self.secret:
            payload.update(_build_signature(self.secret))
        if self.dry_run or not self.webhook_url:
            return NotificationResult(status="dry_run", response=payload)

        response = self._json_post(self.webhook_url, payload, {})
        status = "sent" if not response.get("error") else "failed"
        return NotificationResult(status=status, response=response)


def build_card_payload(
    asset_name: str,
    sample: MarketSample,
    rule: AlertRule,
    change_percent: float | None = None,
) -> dict[str, Any]:
    if rule.rule_type == RuleType.PRICE_BELOW:
        title = f"{asset_name} 价格提醒"
        template = "red"
        fields = [
            _field("当前价格", _format_usd(sample.price_usd)),
            _field("触发条件", f"<= {_format_usd(rule.target_price_usd)}"),
        ]
    else:
        direction_label = "上涨" if rule.direction == RuleDirection.UP else "下跌"
        template = "orange"
        title = f"{asset_name} 涨跌幅提醒"
        fields = [
            _field("当前价格", _format_usd(sample.price_usd)),
            _field("当前涨跌幅", f"{(change_percent or 0.0):.2f}%"),
            _field("触发条件", f"{rule.window_code} {direction_label} >= {rule.target_percent:.2f}%"),
        ]

    fields.append(_field("时间", _format_local_time(sample.sampled_at), is_short=False))

    return {
        "msg_type": "interactive",
        "card": {
            "config": {
                "wide_screen_mode": True,
                "enable_forward": True,
            },
            "header": {
                "template": template,
                "title": {
                    "tag": "plain_text",
                    "content": title,
                },
            },
            "elements": [
                {
                    "tag": "div",
                    "fields": fields,
                }
            ],
        },
    }


def _field(label: str, value: str, is_short: bool = True) -> dict[str, Any]:
    return {
        "is_short": is_short,
        "text": {
            "tag": "lark_md",
            "content": f"**{label}**\n{value}",
        },
    }


def _format_usd(value: float | None) -> str:
    return f"{(value or 0.0):.4f} USD"


def _format_local_time(timestamp) -> str:
    return timestamp.astimezone().strftime("%Y-%m-%d %H:%M:%S %Z")


def _build_signature(secret: str) -> dict[str, str]:
    timestamp = str(int(time.time()))
    string_to_sign = f"{timestamp}\n{secret}"
    digest = hmac.new(
        string_to_sign.encode("utf-8"),
        msg=b"",
        digestmod=hashlib.sha256,
    ).digest()
    sign = base64.b64encode(digest).decode("utf-8")
    return {"timestamp": timestamp, "sign": sign}
