"""yfinance price provider — zero-config fallback for IDX tickers."""
from __future__ import annotations

import logging

import pandas as pd
import yfinance as yf

from ..utils.logging import get_logger
from .base import OHLCV, PriceDataProvider

# Suppress yfinance's own noisy warnings
logging.getLogger("yfinance").setLevel(logging.CRITICAL)

logger = get_logger(__name__)


class YFinanceProvider(PriceDataProvider):
    """Uses yfinance (Yahoo Finance) — supports BBCA.JK format natively."""

    def fetch(self, ticker: str, days: int = 90) -> OHLCV:
        # yfinance accepts period like "90d"; cap at 1y for older tickers
        period = f"{min(days, 365)}d"
        t = yf.Ticker(ticker)
        hist = t.history(period=period, auto_adjust=True)
        if hist.empty:
            raise ValueError(f"yfinance: no data for '{ticker}' (period={period})")
        df = hist.rename(columns={
            "Open": "open",
            "High": "high",
            "Low": "low",
            "Close": "close",
            "Volume": "volume",
        })[["open", "high", "low", "close", "volume"]].copy()
        # Strip timezone so index is plain DatetimeIndex
        df.index = pd.to_datetime(df.index).tz_localize(None)
        df = df.apply(pd.to_numeric, errors="coerce")
        logger.info("yfinance: %d rows for %s", len(df), ticker)
        return OHLCV(ticker=ticker, df=df)
