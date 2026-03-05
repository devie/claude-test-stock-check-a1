from __future__ import annotations

import random
import time
from typing import Any

import requests
from requests.exceptions import HTTPError
from tenacity import (
    retry,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential,
)

from .logging import get_logger

logger = get_logger(__name__)

# Browser-like headers to avoid 403 from bot-protection
_BROWSER_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)
_BROWSER_ACCEPT = (
    "text/html,application/xhtml+xml,application/xml;q=0.9,"
    "image/avif,image/webp,*/*;q=0.8"
)

_SESSION = requests.Session()
_SESSION.headers.update({
    "User-Agent": _BROWSER_UA,
    "Accept": _BROWSER_ACCEPT,
    "Accept-Language": "en-US,en;q=0.9,id;q=0.8",
    "Accept-Encoding": "gzip, deflate",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
})


def _is_retryable(exc: BaseException) -> bool:
    """Retry on network errors AND on HTTP 429/5xx."""
    if isinstance(exc, HTTPError):
        code = exc.response.status_code if exc.response is not None else 0
        return code in (403, 429, 500, 502, 503, 504)
    return isinstance(exc, (requests.Timeout, requests.ConnectionError))


def _retry_wait(retry_state) -> float:
    """Respect Retry-After header on 429; otherwise exponential + jitter."""
    exc = retry_state.outcome.exception()
    if isinstance(exc, HTTPError) and exc.response is not None:
        after = exc.response.headers.get("Retry-After", "")
        try:
            return min(float(after), 60.0)
        except (ValueError, TypeError):
            pass
    attempt = retry_state.attempt_number
    return min(2 ** attempt + random.uniform(0.5, 1.5), 30.0)


@retry(
    retry=retry_if_exception(_is_retryable),
    stop=stop_after_attempt(4),
    wait=wait_exponential(multiplier=1, min=1, max=15),
    reraise=True,
)
def get_json(
    url: str,
    params: dict | None = None,
    headers: dict | None = None,
    timeout: int = 15,
) -> Any:
    """GET with retry (network + 429/5xx); returns parsed JSON."""
    time.sleep(random.uniform(0.05, 0.25))
    resp = _SESSION.get(url, params=params, headers=headers, timeout=timeout)
    if not resp.ok:
        raise HTTPError(
            f"HTTP {resp.status_code} for {resp.url}: {resp.text[:200]}",
            response=resp,
        )
    return resp.json()


@retry(
    retry=retry_if_exception(_is_retryable),
    stop=stop_after_attempt(4),
    wait=wait_exponential(multiplier=1, min=1, max=15),
    reraise=True,
)
def get_html(
    url: str,
    headers: dict | None = None,
    timeout: int = 25,
    referer: str | None = None,
) -> str:
    """GET with retry; returns HTML text. Tolerates partial chunked responses."""
    time.sleep(random.uniform(0.15, 0.45))
    merged = {}
    if referer:
        merged["Referer"] = referer
    if headers:
        merged.update(headers)
    resp = _SESSION.get(url, headers=merged or None, timeout=timeout, stream=True)
    if not resp.ok:
        raise HTTPError(
            f"HTTP {resp.status_code} for {resp.url}",
            response=resp,
        )
    # Stream read: tolerate IncompleteRead / ChunkedEncodingError mid-transfer
    chunks: list[bytes] = []
    try:
        for chunk in resp.iter_content(chunk_size=8192):
            if chunk:
                chunks.append(chunk)
    except Exception as exc:
        if not chunks:
            raise
        logger.debug("get_html partial read (%d bytes): %s", sum(len(c) for c in chunks), exc)
    return b"".join(chunks).decode(resp.encoding or "utf-8", errors="replace")
