"""Microsoft Teams webhook notifier."""
from __future__ import annotations

import requests

from ..utils.logging import get_logger

logger = get_logger(__name__)


class TeamsNotifier:
    def __init__(self, webhook_url: str) -> None:
        self._url = webhook_url

    def send(self, alerts: list[dict]) -> None:
        if not alerts or not self._url:
            return
        lines = "\n".join(
            f"**{a.get('ticker','?')}** score={a.get('score','?')} "
            f"severity={a.get('severity','?')} rules={a.get('rules_triggered', [])}"
            for a in alerts[:15]
        )
        payload = {
            "@type": "MessageCard",
            "@context": "http://schema.org/extensions",
            "themeColor": "FF0000",
            "summary": f"IDX Anomaly: {len(alerts)} alert(s)",
            "sections": [
                {
                    "activityTitle": f"IDX Anomaly Scanner — {len(alerts)} alert(s)",
                    "text": lines,
                }
            ],
        }
        try:
            resp = requests.post(self._url, json=payload, timeout=10)
            resp.raise_for_status()
            logger.info("teams: sent %d alerts", len(alerts))
        except Exception as exc:
            logger.error("teams notify failed: %s", exc)
