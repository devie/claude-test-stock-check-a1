"""IDX UMA scraper — file-backed 24h cache, fallback to stale on error."""
from __future__ import annotations

import json
import re
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path

from bs4 import BeautifulSoup

from ..utils.http import get_html, get_json
from ..utils.logging import get_logger
from .base import UMAEntry, UMAProvider

logger = get_logger(__name__)

# Primary: newer idx.id domain + path specified by req
_UMA_HTML_PRIMARY  = "https://www.idx.id/en/news/unusual-market-activity-uma/"
_UMA_HTML_FALLBACK = "https://www.idx.id/id/berita/aktivitas-perdagangan-tidak-wajar-uma/"
_UMA_JSON_PRIMARY  = "https://www.idx.id/umbraco/Surface/NewsAjax/GetNewsAjax"
_UMA_JSON_FALLBACK = "https://www.idx.co.id/umbraco/Surface/NewsAjax/GetNewsAjax"

# Matches IDX SSR-embedded PDF paths: 20260304-WAS_UMA_MLPT.pdf
_PDF_PATH_RE = re.compile(r"(\d{8})-WAS_UMA_([A-Z]{2,5})\.pdf")
_TICKER_RE = re.compile(r"\b([A-Z]{3,5})\b")
_SKIP_WORDS = {
    "THE", "IDX", "UMA", "BEI", "OJK", "FROM", "DATE", "CODE", "NAME",
    "STOCK", "SHARE", "LIST", "AND", "FOR", "NEW", "LTD", "TBK", "SAHAM",
    "WITH", "HAS", "NOT", "BUT", "ARE", "ALL", "INC", "PTE", "COR",
}
_DATE_FMTS = ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y", "%B %d, %Y", "%d %B %Y")

_mem_cache: list[UMAEntry] | None = None
_mem_ts: datetime | None = None
_mem_lock = threading.Lock()


class IDXUMAScraper(UMAProvider):
    def __init__(
        self,
        url: str = _UMA_HTML_PRIMARY,
        max_count: int = 20,
        cache_file: str = "data/uma_cache.json",
        cache_ttl_hours: int = 24,
    ) -> None:
        self._url = url
        self._max = max_count
        self._cache_file = cache_file
        self._ttl_hours = cache_ttl_hours

    def fetch(self) -> list[UMAEntry]:
        # 1. In-memory hot cache (1-min TTL for repeated calls within same process)
        global _mem_cache, _mem_ts
        with _mem_lock:
            if _mem_cache is not None and _mem_ts is not None:
                age_s = (datetime.now(timezone.utc) - _mem_ts).total_seconds()
                if age_s < 60:
                    return _mem_cache[: self._max]

        # 2. File cache (24h TTL)
        cached = _load_file_cache(self._cache_file, self._ttl_hours)
        if cached is not None:
            logger.debug("uma_idx: file cache hit (%d entries)", len(cached))
            with _mem_lock:
                _mem_cache, _mem_ts = cached, datetime.now(timezone.utc)
            return cached[: self._max]

        # 3. Live fetch
        entries = _fetch_live(self._url)

        if entries:
            _save_file_cache(entries, self._cache_file, self._ttl_hours)
        else:
            # 4. Stale fallback — load expired cache rather than returning nothing
            stale = _load_file_cache(self._cache_file, ttl_hours=999999)
            if stale:
                logger.warning(
                    "uma_idx: live fetch returned 0 entries; using stale cache (%d)",
                    len(stale),
                )
                entries = stale

        with _mem_lock:
            _mem_cache, _mem_ts = entries, datetime.now(timezone.utc)
        return entries[: self._max]


# ── file cache helpers ────────────────────────────────────────────────────────

def _load_file_cache(cache_file: str, ttl_hours: int) -> list[UMAEntry] | None:
    p = Path(cache_file)
    if not p.exists():
        return None
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        ts = datetime.fromisoformat(data["timestamp"])
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        age_h = (datetime.now(timezone.utc) - ts).total_seconds() / 3600
        if age_h >= ttl_hours:
            return None
        return [
            UMAEntry(
                ticker=e["ticker"],
                date_listed=e["date_listed"],
                reason=e["reason"],
            )
            for e in data.get("entries", [])
        ]
    except Exception as exc:
        logger.debug("uma_idx: cache read error: %s", exc)
        return None


def _save_file_cache(
    entries: list[UMAEntry], cache_file: str, ttl_hours: int
) -> None:
    p = Path(cache_file)
    p.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "ttl_hours": ttl_hours,
        "entries": [
            {"ticker": e.ticker, "date_listed": e.date_listed, "reason": e.reason}
            for e in entries
        ],
    }
    p.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    logger.debug("uma_idx: saved %d entries to %s", len(entries), cache_file)


# ── live fetch strategies ─────────────────────────────────────────────────────

def _fetch_live(html_url: str) -> list[UMAEntry]:
    """Try JSON API (primary + fallback domains) → HTML scrape → empty list."""
    for api_url, referer in (
        (_UMA_JSON_PRIMARY,  "https://www.idx.id/"),
        (_UMA_JSON_FALLBACK, "https://www.idx.co.id/"),
    ):
        try:
            data = get_json(
                api_url,
                params={"category": "uma", "page": 1, "pagesize": 50},
                headers={
                    "Referer": referer,
                    "X-Requested-With": "XMLHttpRequest",
                    "Accept": "application/json, text/javascript, */*; q=0.01",
                },
            )
            entries = _parse_uma_json(data)
            if entries:
                logger.info("uma_idx: %d entries via JSON API %s", len(entries), api_url)
                return entries
        except Exception as exc:
            logger.debug("uma_idx JSON API %s failed: %s", api_url, exc)

    # HTML fallback — try primary then Indonesian-language path (same domain)
    for url, referer in (
        (html_url,           "https://www.idx.id/"),
        (_UMA_HTML_FALLBACK, "https://www.idx.id/"),
    ):
        try:
            html = get_html(
                url,
                referer=referer,
                headers={
                    "Accept": (
                        "text/html,application/xhtml+xml,"
                        "application/xml;q=0.9,*/*;q=0.8"
                    ),
                    "Sec-Fetch-Dest": "document",
                    "Sec-Fetch-Mode": "navigate",
                    "Sec-Fetch-Site": "same-origin",
                },
            )
            entries = parse_uma_html(html)
            if entries:
                logger.info("uma_idx: %d entries via HTML %s", len(entries), url)
                return entries
        except Exception as exc:
            logger.debug("uma_idx HTML %s failed: %s", url, exc)

    logger.warning("uma_idx: all strategies failed — returning empty list")
    return []


# ── parsers ───────────────────────────────────────────────────────────────────

def _parse_uma_json(data: object) -> list[UMAEntry]:
    if not isinstance(data, (dict, list)):
        return []
    items: list = data if isinstance(data, list) else (
        data.get("data") or data.get("items") or data.get("results") or []
    )
    entries: list[UMAEntry] = []
    seen: set[str] = set()
    for item in items:
        if not isinstance(item, dict):
            continue
        raw = (
            item.get("stockCode") or item.get("code") or
            item.get("emiten") or item.get("ticker") or ""
        )
        if raw:
            ticker: str | None = _normalize_ticker(str(raw).strip().upper())
        else:
            text = " ".join(str(v) for v in item.values() if isinstance(v, str))
            ticker = _find_ticker([text])
        if not ticker or ticker in seen:
            continue
        seen.add(ticker)
        reason = (
            item.get("title") or item.get("description") or
            item.get("content") or ""
        )[:300]
        entries.append(UMAEntry(
            ticker=ticker,
            date_listed=_extract_date_from_dict(item),
            reason=reason,
        ))
    return entries


def _parse_uma_pdf_paths(html: str, days: int = 90) -> list[UMAEntry]:
    """Extract UMA tickers from Nuxt SSR-embedded PDF paths.

    IDX's new Nuxt.js site embeds paths like ``20260304-WAS_UMA_MLPT.pdf``
    directly in the SSR HTML. Filter to entries within the last ``days`` days
    so we return recent UMA announcements, not the full historical archive.
    """
    cutoff = datetime.now(timezone.utc).date() - timedelta(days=days)

    seen: set[str] = set()
    entries: list[UMAEntry] = []
    for m in _PDF_PATH_RE.finditer(html):
        date_str, raw_ticker = m.group(1), m.group(2)
        try:
            entry_date = datetime.strptime(date_str, "%Y%m%d").date()
        except ValueError:
            continue
        if entry_date < cutoff:
            continue
        ticker = _normalize_ticker(raw_ticker)
        if ticker in seen:
            continue
        seen.add(ticker)
        entries.append(UMAEntry(
            ticker=ticker,
            date_listed=entry_date.isoformat(),
            reason=f"UMA announcement {entry_date.isoformat()}",
        ))

    # Sort by date descending (most recent first)
    entries.sort(key=lambda e: e.date_listed, reverse=True)
    return entries


def parse_uma_html(html: str) -> list[UMAEntry]:
    # Strategy 0: IDX Nuxt SSR — PDF path pattern (fast regex, no BS4 needed)
    entries = _parse_uma_pdf_paths(html)
    if entries:
        return entries

    soup = BeautifulSoup(html, "html.parser")
    entries = []
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

    # Strategy 2: announcement items / data-code attributes
    if not entries:
        for item in soup.select(
            "li, .announcement-item, .news-item, article, .post, [data-code]"
        ):
            code = item.get("data-code") or item.get("data-stock")
            ticker = _normalize_ticker(code.strip().upper()) if code else _find_ticker([item.get_text(strip=True)])
            if ticker and ticker not in seen and len(item.get_text(strip=True)) >= 5:
                seen.add(ticker)
                entries.append(UMAEntry(
                    ticker=ticker,
                    date_listed=datetime.now(timezone.utc).date().isoformat(),
                    reason=item.get_text(strip=True)[:300],
                ))

    # Strategy 3: scan <a> link text and href for 4-letter ticker codes
    if not entries:
        for a in soup.find_all("a", href=True):
            text = a.get_text(strip=True)
            href = a["href"]
            ticker = _find_ticker([text, href])
            if ticker and ticker not in seen:
                seen.add(ticker)
                entries.append(UMAEntry(
                    ticker=ticker,
                    date_listed=datetime.now(timezone.utc).date().isoformat(),
                    reason=text[:300],
                ))

    return entries


# ── helpers ───────────────────────────────────────────────────────────────────

def _find_ticker(candidates: list[str]) -> str | None:
    for text in candidates:
        for m in _TICKER_RE.finditer(text.upper()):
            raw = m.group(1)
            if raw not in _SKIP_WORDS and len(raw) >= 3:
                return _normalize_ticker(raw)
    return None


def _normalize_ticker(raw: str) -> str:
    return raw if raw.endswith(".JK") else f"{raw}.JK"


def _extract_date(cells: list[str]) -> str:
    for cell in cells:
        for fmt in _DATE_FMTS:
            try:
                return datetime.strptime(cell.strip(), fmt).date().isoformat()
            except ValueError:
                continue
    return datetime.now(timezone.utc).date().isoformat()


def _extract_date_from_dict(item: dict) -> str:
    for key in ("date", "publishedDate", "created", "time", "tanggal"):
        v = str(item.get(key, ""))
        for fmt in _DATE_FMTS:
            try:
                return datetime.strptime(v[:10], fmt).date().isoformat()
            except ValueError:
                continue
    return datetime.now(timezone.utc).date().isoformat()
