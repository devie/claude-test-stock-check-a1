"""SMTP email notifier."""
from __future__ import annotations

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from ..utils.logging import get_logger

logger = get_logger(__name__)


class EmailNotifier:
    def __init__(
        self,
        host: str,
        user: str,
        password: str,
        to: str,
        port: int = 587,
    ) -> None:
        self._host = host
        self._user = user
        self._pass = password
        self._to = to
        self._port = port

    def send(self, alerts: list[dict]) -> None:
        if not alerts or not self._host:
            return
        subject = f"[IDX Anomaly] {len(alerts)} alert(s)"
        rows = "\n".join(
            f"{a.get('ticker','?')}: score={a.get('score','?')} "
            f"severity={a.get('severity','?')} rules={a.get('rules_triggered', [])}"
            for a in alerts
        )
        body = f"IDX Anomaly Scanner detected {len(alerts)} alert(s):\n\n{rows}"
        msg = MIMEMultipart()
        msg["From"] = self._user
        msg["To"] = self._to
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain"))
        try:
            with smtplib.SMTP(self._host, self._port) as srv:
                srv.starttls()
                srv.login(self._user, self._pass)
                srv.sendmail(self._user, self._to, msg.as_string())
            logger.info("email sent to %s (%d alerts)", self._to, len(alerts))
        except Exception as exc:
            logger.error("email notify failed: %s", exc)
