"""Finnhub fundamentals provider with IDX symbol formats and yfinance fallback."""
from __future__ import annotations

import logging
import threading

from cachetools import TTLCache
from requests.exceptions import HTTPError

from ..utils.http import get_json
from ..utils.logging import get_logger
from .base import Fundamentals, FundamentalsProvider

logging.getLogger("yfinance").setLevel(logging.CRITICAL)

logger = get_logger(__name__)

_BASE = "https://finnhub.io/api/v1"

# 4-hour TTL cache (fundamentals don't change intraday)
_cache: TTLCache = TTLCache(maxsize=200, ttl=14400)
_cache_lock = threading.Lock()


class FinnhubProvider(FundamentalsProvider):
    def __init__(self, api_key: str) -> None:
        self._key = api_key

    def fetch(self, ticker: str) -> Fundamentals:
        with _cache_lock:
            if ticker in _cache:
                return _cache[ticker]

        result = self._fetch_uncached(ticker)

        with _cache_lock:
            _cache[ticker] = result
        return result

    def _fetch_uncached(self, ticker: str) -> Fundamentals:
        if not self._key:
            logger.info("finnhub: no API key, using yfinance for %s", ticker)
            return _yf_fundamentals(ticker)

        bare = ticker.split(".")[0]  # BBCA.JK → BBCA
        # Finnhub IDX format variants to try
        candidates = [bare, f"IDX:{bare}", f"BEI:{bare}"]

        for symbol in candidates:
            try:
                data = get_json(
                    f"{_BASE}/stock/metric",
                    params={"symbol": symbol, "token": self._key, "metric": "all"},
                )
                m = data.get("metric", {})
                bvps = _to_float(
                    m.get("bookValuePerShareAnnual") or m.get("bookValuePerShareQuarterly")
                )
                pbv = _to_float(m.get("pbAnnual") or m.get("pbQuarterly"))
                if bvps is not None or pbv is not None:
                    logger.info("finnhub %s (sym=%s): bvps=%s pbv=%s", ticker, symbol, bvps, pbv)
                    return Fundamentals(ticker=ticker, bvps=bvps, pbv_ttm=pbv, extra=m)
            except HTTPError as exc:
                code = exc.response.status_code if exc.response is not None else 0
                if code == 403:
                    logger.warning("finnhub 403 for %s — check API key/plan", ticker)
                    break  # no point retrying other formats
                logger.debug("finnhub HTTP %s for symbol=%s", code, symbol)
            except Exception as exc:
                logger.debug("finnhub error for %s (sym=%s): %s", ticker, symbol, exc)

        logger.info("finnhub: no data for %s, falling back to yfinance", ticker)
        return _yf_fundamentals(ticker)


def _yf_fundamentals(ticker: str) -> Fundamentals:
    try:
        import yfinance as yf
        info = yf.Ticker(ticker).info or {}
        bvps = _to_float(info.get("bookValue"))
        pbv = _to_float(info.get("priceToBook"))
        logger.info("yfinance fundamentals %s: bvps=%s pbv=%s", ticker, bvps, pbv)
        return Fundamentals(ticker=ticker, bvps=bvps, pbv_ttm=pbv, extra=info)
    except Exception as exc:
        logger.warning("yfinance fundamentals failed for %s: %s", ticker, exc)
        return Fundamentals(ticker=ticker, bvps=None, pbv_ttm=None)


def _to_float(v: object) -> float | None:
    try:
        return float(v) if v is not None else None
    except (TypeError, ValueError):
        return None
