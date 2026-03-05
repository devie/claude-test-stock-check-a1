"""OHLC.dev price provider via RapidAPI, with yfinance fallback."""
from __future__ import annotations

from datetime import datetime, timedelta

import pandas as pd
from requests.exceptions import HTTPError

from ..utils.http import get_json
from ..utils.logging import get_logger
from .base import OHLCV, PriceDataProvider

logger = get_logger(__name__)

_BASE = "https://ohlc.p.rapidapi.com"
_HOST = "ohlc.p.rapidapi.com"


class OHLCDevProvider(PriceDataProvider):
    """OHLC.dev via RapidAPI. Falls back to yfinance on 404/403."""

    def __init__(self, api_key: str) -> None:
        self._api_key = api_key
        self._headers = {
            "x-rapidapi-key": api_key,
            "x-rapidapi-host": _HOST,
        }

    def fetch(self, ticker: str, days: int = 90) -> OHLCV:
        if not self._api_key:
            logger.info("ohlcdev: no API key, using yfinance for %s", ticker)
            return _yf_fallback(ticker, days)

        end = datetime.utcnow().date()
        start = end - timedelta(days=days)
        params = {
            "symbol": ticker,        # IDX tickers: BBCA.JK
            "from": str(start),
            "to": str(end),
            "interval": "1d",
        }
        try:
            data = get_json(f"{_BASE}/history", params=params, headers=self._headers)
            rows = data.get("data", data) if isinstance(data, dict) else data
            df = _parse_rows(rows)
            if df.empty:
                raise ValueError("ohlcdev returned empty data")
            logger.info("ohlcdev: %d rows for %s", len(df), ticker)
            return OHLCV(ticker=ticker, df=df)
        except (HTTPError, ValueError) as exc:
            status = getattr(getattr(exc, "response", None), "status_code", None)
            logger.warning(
                "ohlcdev failed for %s (HTTP %s: %s) — falling back to yfinance",
                ticker, status or "?", exc,
            )
            return _yf_fallback(ticker, days)


def _yf_fallback(ticker: str, days: int) -> OHLCV:
    from .price_yfinance import YFinanceProvider
    return YFinanceProvider().fetch(ticker, days)


def _parse_rows(rows: list[dict]) -> pd.DataFrame:
    if not rows:
        return pd.DataFrame(columns=["open", "high", "low", "close", "volume"])
    df = pd.DataFrame(rows)
    df.columns = [c.lower() for c in df.columns]
    date_col = next((c for c in df.columns if c in ("date", "datetime", "t", "time")), None)
    if date_col:
        df["date"] = pd.to_datetime(df[date_col])
        if date_col != "date":
            df = df.drop(columns=[date_col])
    else:
        df["date"] = pd.to_datetime(df.index)
    df = df.set_index("date").sort_index()
    for col in ("open", "high", "low", "close", "volume"):
        if col not in df.columns:
            df[col] = float("nan")
    return df[["open", "high", "low", "close", "volume"]].apply(pd.to_numeric, errors="coerce")
