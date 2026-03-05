from __future__ import annotations

import random
import time
from typing import Any

import requests
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from .logging import get_logger

logger = get_logger(__name__)

_SESSION = requests.Session()
_SESSION.headers.update({"User-Agent": "idx-anomaly/1.0"})


@retry(
    retry=retry_if_exception_type((requests.Timeout, requests.ConnectionError)),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    reraise=True,
)
def get_json(
    url: str,
    params: dict | None = None,
    headers: dict | None = None,
    timeout: int = 15,
) -> Any:
    """GET with retry + jitter; returns parsed JSON."""
    time.sleep(random.uniform(0.05, 0.25))
    resp = _SESSION.get(url, params=params, headers=headers, timeout=timeout)
    resp.raise_for_status()
    return resp.json()


@retry(
    retry=retry_if_exception_type((requests.Timeout, requests.ConnectionError)),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    reraise=True,
)
def get_html(url: str, headers: dict | None = None, timeout: int = 20) -> str:
    """GET with retry + jitter; returns HTML text."""
    time.sleep(random.uniform(0.1, 0.4))
    resp = _SESSION.get(url, headers=headers, timeout=timeout)
    resp.raise_for_status()
    return resp.text
