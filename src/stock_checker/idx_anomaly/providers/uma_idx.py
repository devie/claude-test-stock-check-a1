"""IDX UMA (Unusual Market Activity) scraper with caching and fallback."""
from __future__ import annotations

import re
import threading
from datetime import datetime, timezone

from bs4 import BeautifulSoup
from cachetools import TTLCache

from ..utils.http import get_html, get_json
from ..utils.logging import get_logger
from .base import UMAEntry, UMAProvider

logger = get_logger(__name__)

# IDX website changed to SPA; try the JSON API endpoint first, then HTML fallback
_UMA_API = "https://www.idx.co.id/umbraco/Surface/NewsAjax/GetNewsAjax"
_UMA_HTML = "https://www.idx.co.id/en/news/unusual-market-activity/"
_IDX_REFERER = "https://www.idx.co.id/"

_TICKER_RE = re.compile(r"\b([A-Z]{3,5})\b")
_SKIP_WORDS = {
    "THE", "IDX", "UMA", "BEI", "OJK", "FROM", "DATE", "CODE", "NAME",
    "STOCK", "SHARE", "LIST", "AND", "FOR", "NEW", "LTD", "TBK", "SAHAM",
    "WITH", "HAS", "NOT", "BUT", "ARE", "ALL", "INC", "PTE", "COR",
}
_DATE_FMTS = ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y", "%B %d, %Y", "%d %B %Y")

# 1-hour TTL cache — shared across all instances, thread-safe
_cache: TTLCache = TTLCache(maxsize=4, ttl=3600)
_cache_lock = threading.Lock()


class IDXUMAScraper(UMAProvider):
    def __init__(self, url: str = _UMA_HTML) -> None:
        self._url = url

    def fetch(self) -> list[UMAEntry]:
        with _cache_lock:
            if "uma" in _cache:
                logger.debug("uma_idx: cache hit")
                return _cache["uma"]

        entries = _fetch_with_fallback(self._url)

        with _cache_lock:
            _cache["uma"] = entries
        return entries


def _fetch_with_fallback(html_url: str) -> list[UMAEntry]:
    """Try JSON API → HTML scrape → empty list."""
    # Strategy 1: IDX AJAX JSON endpoint
    try:
        data = get_json(
            _UMA_API,
            params={"category": "uma", "page": 1, "pagesize": 50},
            headers={
                "Referer": _IDX_REFERER,
                "X-Requested-With": "XMLHttpRequest",
                "Accept": "application/json, text/javascript, */*; q=0.01",
            },
        )
        entries = _parse_uma_json(data)
        if entries:
            logger.info("uma_idx: %d entries via JSON API", len(entries))
            return entries
    except Exception as exc:
        logger.debug("uma_idx JSON API failed (%s), trying HTML", exc)

    # Strategy 2: HTML scrape with browser headers
    try:
        html = get_html(
            html_url,
            referer=_IDX_REFERER,
            headers={
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Sec-Fetch-Dest": "document",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Site": "same-origin",
            },
        )
        entries = parse_uma_html(html)
        if entries:
            logger.info("uma_idx: %d entries via HTML scrape", len(entries))
        else:
            logger.warning(
                "uma_idx: HTML page returned 0 entries — "
                "page may require JavaScript rendering"
            )
        return entries
    except Exception as exc:
        logger.warning("uma_idx: HTML scrape failed (%s) — returning empty list", exc)
        return []


def _parse_uma_json(data: object) -> list[UMAEntry]:
    """Parse IDX AJAX JSON response."""
    if not isinstance(data, (dict, list)):
        return []
    items = data if isinstance(data, list) else (
        data.get("data") or data.get("items") or data.get("results") or []
    )
    entries: list[UMAEntry] = []
    seen: set[str] = set()
    for item in items:
        if not isinstance(item, dict):
            continue
        # Look for ticker in common JSON field names
        raw_ticker = (
            item.get("stockCode") or item.get("code") or
            item.get("emiten") or item.get("ticker") or ""
        )
        if raw_ticker:
            ticker = _normalize_ticker(str(raw_ticker).strip().upper())
        else:
            # Fall back to scanning text fields
            text = " ".join(str(v) for v in item.values() if isinstance(v, str))
            ticker = _find_ticker([text])
        if not ticker or ticker in seen:
            continue
        seen.add(ticker)
        date_str = _extract_date_from_dict(item)
        reason = (
            item.get("title") or item.get("description") or
            item.get("content") or str(item)
        )[:300]
        entries.append(UMAEntry(ticker=ticker, date_listed=date_str, reason=reason))
    return entries


def _extract_date_from_dict(item: dict) -> str:
    for key in ("date", "publishedDate", "created", "time", "tanggal"):
        v = item.get(key, "")
        if v:
            for fmt in _DATE_FMTS:
                try:
                    return datetime.strptime(str(v)[:10], fmt).date().isoformat()
                except ValueError:
                    continue
    return datetime.now(timezone.utc).date().isoformat()


def parse_uma_html(html: str) -> list[UMAEntry]:
    """Parse IDX UMA page HTML — multiple selector strategies."""
    soup = BeautifulSoup(html, "html.parser")
    entries: list[UMAEntry] = []
    seen: set[str] = set()

    # Strategy 1: table rows
    for row in soup.select("table tr"):
        cells = [td.get_text(strip=True) for td in row.find_all(["td", "th"])]
        if len(cells) < 2:
            continue
        ticker = _find_ticker(cells[:4])
        if ticker and ticker not in seen:
            seen.add(ticker)
            entries.append(UMAEntry(
                ticker=ticker,
                date_listed=_extract_date(cells),
                reason=" | ".join(cells)[:300],
            ))

    # Strategy 2: structured announcement items
    if not entries:
        for item in soup.select(
            "li, .announcement-item, .news-item, "
            "article, .post, .item-uma, [data-code]"
        ):
            # Check for data-code attribute (IDX sometimes uses this)
            code = item.get("data-code") or item.get("data-stock")
            if code:
                ticker = _normalize_ticker(code.strip().upper())
            else:
                text = item.get_text(strip=True)
                if len(text) < 5:
                    continue
                ticker = _find_ticker([text])
            if ticker and ticker not in seen:
                seen.add(ticker)
                text = item.get_text(strip=True)
                entries.append(UMAEntry(
                    ticker=ticker,
                    date_listed=datetime.now(timezone.utc).date().isoformat(),
                    reason=text[:300],
                ))

    logger.debug("uma_idx parse_html: %d entries", len(entries))
    return entries


def _find_ticker(candidates: list[str]) -> str | None:
    for text in candidates:
        for m in _TICKER_RE.finditer(text.upper()):
            raw = m.group(1)
            if raw not in _SKIP_WORDS and len(raw) >= 3:
                return _normalize_ticker(raw)
    return None


def _normalize_ticker(raw: str) -> str:
    """Ensure IDX ticker has .JK suffix."""
    if raw.endswith(".JK"):
        return raw
    return f"{raw}.JK"


def _extract_date(cells: list[str]) -> str:
    for cell in cells:
        for fmt in _DATE_FMTS:
            try:
                return datetime.strptime(cell.strip(), fmt).date().isoformat()
            except ValueError:
                continue
    return datetime.now(timezone.utc).date().isoformat()
