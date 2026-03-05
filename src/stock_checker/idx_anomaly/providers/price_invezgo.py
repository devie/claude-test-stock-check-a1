"""Invezgo price provider (alternative to OHLC.dev)."""
from __future__ import annotations

from datetime import datetime, timedelta

import pandas as pd

from ..utils.http import get_json
from ..utils.logging import get_logger
from .base import OHLCV, PriceDataProvider

logger = get_logger(__name__)

_BASE = "https://api.invezgo.com/v1"


class InvezgoProvider(PriceDataProvider):
    def __init__(self, api_key: str) -> None:
        self._key = api_key

    def fetch(self, ticker: str, days: int = 90) -> OHLCV:
        end = datetime.utcnow().date()
        start = end - timedelta(days=days)
        params = {
            "symbol": ticker,
            "startDate": str(start),
            "endDate": str(end),
            "apikey": self._key,
        }
        data = get_json(f"{_BASE}/stock/candles", params=params)
        candles = data.get("candles", data.get("data", []))
        df = _parse_candles(candles)
        logger.info("invezgo: %s rows for %s", len(df), ticker)
        return OHLCV(ticker=ticker, df=df)


def _parse_candles(candles: list[dict]) -> pd.DataFrame:
    if not candles:
        return pd.DataFrame(columns=["open", "high", "low", "close", "volume"])
    df = pd.DataFrame(candles)
    df.columns = [c.lower() for c in df.columns]
    date_col = next((c for c in df.columns if "date" in c or "time" in c), None)
    if date_col:
        df["date"] = pd.to_datetime(df[date_col])
        if date_col != "date":
            df = df.drop(columns=[date_col])
        df = df.set_index("date").sort_index()
    for col in ("open", "high", "low", "close", "volume"):
        if col not in df.columns:
            df[col] = float("nan")
    return df[["open", "high", "low", "close", "volume"]].apply(pd.to_numeric, errors="coerce")
