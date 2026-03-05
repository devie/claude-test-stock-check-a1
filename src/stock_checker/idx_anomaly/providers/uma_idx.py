"""IDX UMA (Unusual Market Activity) page scraper."""
from __future__ import annotations

import re
from datetime import datetime

from bs4 import BeautifulSoup

from ..utils.http import get_html
from ..utils.logging import get_logger
from .base import UMAEntry, UMAProvider

logger = get_logger(__name__)

_UMA_URL = "https://www.idx.co.id/en/news/unusual-market-activity/"
_TICKER_RE = re.compile(r"\b([A-Z]{3,5})\b")
_SKIP_WORDS = {
    "THE", "IDX", "UMA", "BEI", "OJK", "FROM", "DATE", "CODE", "NAME",
    "STOCK", "SHARE", "LIST", "AND", "FOR", "NEW", "LTD", "TBK",
}
_DATE_FMTS = ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y", "%B %d, %Y", "%d %B %Y")


class IDXUMAScraper(UMAProvider):
    def __init__(self, url: str = _UMA_URL) -> None:
        self._url = url

    def fetch(self) -> list[UMAEntry]:
        html = get_html(self._url)
        return parse_uma_html(html)


def parse_uma_html(html: str) -> list[UMAEntry]:
    """Parse IDX UMA page HTML and return structured entries."""
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
            entries.append(
                UMAEntry(
                    ticker=ticker,
                    date_listed=_extract_date(cells),
                    reason=" | ".join(cells)[:300],
                )
            )

    # Strategy 2: announcement items / list items (fallback)
    if not entries:
        for item in soup.select("li, .announcement-item, .news-item, article, .post"):
            text = item.get_text(strip=True)
            if len(text) < 10:
                continue
            ticker = _find_ticker([text])
            if ticker and ticker not in seen:
                seen.add(ticker)
                entries.append(
                    UMAEntry(
                        ticker=ticker,
                        date_listed=datetime.utcnow().date().isoformat(),
                        reason=text[:300],
                    )
                )

    logger.info("uma_idx: scraped %d entries from %s", len(entries), _UMA_URL)
    return entries


def _find_ticker(candidates: list[str]) -> str | None:
    for text in candidates:
        for m in _TICKER_RE.finditer(text.upper()):
            raw = m.group(1)
            if raw not in _SKIP_WORDS and len(raw) >= 3:
                return _normalize_ticker(raw)
    return None


def _normalize_ticker(raw: str) -> str:
    if raw.endswith(".JK"):
        return raw
    return f"{raw}.JK"


def _extract_date(cells: list[str]) -> str:
    for cell in cells:
        cell = cell.strip()
        for fmt in _DATE_FMTS:
            try:
                return datetime.strptime(cell, fmt).date().isoformat()
            except ValueError:
                continue
    return datetime.utcnow().date().isoformat()
