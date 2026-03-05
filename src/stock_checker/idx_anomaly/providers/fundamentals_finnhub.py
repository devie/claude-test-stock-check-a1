"""Finnhub fundamentals provider (BVPS, PBV)."""
from __future__ import annotations

from ..utils.http import get_json
from ..utils.logging import get_logger
from .base import Fundamentals, FundamentalsProvider

logger = get_logger(__name__)

_BASE = "https://finnhub.io/api/v1"


class FinnhubProvider(FundamentalsProvider):
    def __init__(self, api_key: str) -> None:
        self._key = api_key

    def fetch(self, ticker: str) -> Fundamentals:
        # IDX tickers: BBCA.JK → strip exchange suffix for Finnhub
        symbol = ticker.split(".")[0] if "." in ticker else ticker
        params = {"symbol": symbol, "token": self._key, "metric": "all"}
        try:
            data = get_json(f"{_BASE}/stock/metric", params=params)
            m = data.get("metric", {})
            bvps = m.get("bookValuePerShareAnnual") or m.get("bookValuePerShareQuarterly")
            pbv = m.get("pbAnnual") or m.get("pbQuarterly")
            logger.info("finnhub %s: bvps=%s pbv=%s", ticker, bvps, pbv)
            return Fundamentals(ticker=ticker, bvps=_to_float(bvps), pbv_ttm=_to_float(pbv), extra=m)
        except Exception as exc:
            logger.warning("finnhub fetch failed for %s: %s", ticker, exc)
            return Fundamentals(ticker=ticker, bvps=None, pbv_ttm=None)


def _to_float(v: object) -> float | None:
    try:
        return float(v) if v is not None else None
    except (TypeError, ValueError):
        return None
