"""Enhanced data fetcher with TTL caching."""

import logging
from cachetools import TTLCache
import yfinance as yf

logging.getLogger("yfinance").setLevel(logging.CRITICAL)

# Cache: max 100 tickers, 5-minute TTL
_ticker_cache = TTLCache(maxsize=100, ttl=300)
_info_cache = TTLCache(maxsize=100, ttl=300)


def get_ticker(symbol):
    """Get or create a cached yfinance Ticker object."""
    if symbol not in _ticker_cache:
        _ticker_cache[symbol] = yf.Ticker(symbol)
    return _ticker_cache[symbol]


def get_info(symbol):
    """Get cached ticker info dict. Falls back to fast_info on auth errors."""
    if symbol not in _info_cache:
        ticker = get_ticker(symbol)
        info = {}
        try:
            info = ticker.info or {}
        except Exception:
            pass

        # If info is empty or missing key fields, merge in fast_info
        if not info or not info.get("currentPrice"):
            try:
                fi = ticker.fast_info
                fast = {
                    "marketCap": fi.get("marketCap"),
                    "currentPrice": fi.get("lastPrice"),
                    "regularMarketPrice": fi.get("lastPrice"),
                    "fiftyTwoWeekHigh": fi.get("yearHigh"),
                    "fiftyTwoWeekLow": fi.get("yearLow"),
                    "averageVolume": fi.get("threeMonthAverageVolume"),
                    "sharesOutstanding": fi.get("shares"),
                    "currency": fi.get("currency"),
                    "exchange": fi.get("exchange"),
                }
                # Merge: fast_info fills gaps, info takes precedence
                merged = {k: v for k, v in fast.items() if v is not None}
                merged.update({k: v for k, v in info.items() if v is not None})
                info = merged
            except Exception:
                pass

        _info_cache[symbol] = info
    return _info_cache[symbol]


def get_history(symbol, period="1y"):
    """Fetch price history DataFrame."""
    ticker = get_ticker(symbol)
    hist = ticker.history(period=period)
    if hist.empty:
        raise ValueError(f"No price data for '{symbol}'")
    return hist


def get_financials(symbol):
    """Get income statement (annual)."""
    ticker = get_ticker(symbol)
    df = ticker.financials
    if df is None or df.empty:
        return None
    return df


def get_quarterly_financials(symbol):
    """Get income statement (quarterly)."""
    ticker = get_ticker(symbol)
    df = ticker.quarterly_financials
    if df is None or df.empty:
        return None
    return df


def get_balance_sheet(symbol):
    """Get balance sheet (annual)."""
    ticker = get_ticker(symbol)
    df = ticker.balance_sheet
    if df is None or df.empty:
        return None
    return df


def get_cashflow(symbol):
    """Get cash flow statement (annual)."""
    ticker = get_ticker(symbol)
    df = ticker.cashflow
    if df is None or df.empty:
        return None
    return df


def get_quarterly_cashflow(symbol):
    """Get cash flow statement (quarterly)."""
    ticker = get_ticker(symbol)
    df = ticker.quarterly_cashflow
    if df is None or df.empty:
        return None
    return df


def clear_cache():
    """Clear all caches."""
    _ticker_cache.clear()
    _info_cache.clear()
