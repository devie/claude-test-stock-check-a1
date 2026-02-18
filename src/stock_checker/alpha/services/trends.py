"""YoY/QoQ trend analysis service."""

import math
import numpy as np
from stock_checker.alpha.services.data_fetcher import (
    get_financials, get_quarterly_financials, get_balance_sheet, get_cashflow
)
from stock_checker.alpha.calculations.growth import calc_growth_series, calc_cagr


def _safe(val):
    if val is None:
        return None
    if isinstance(val, (np.integer,)):
        return int(val)
    if isinstance(val, (np.floating, float)):
        if math.isnan(val) or math.isinf(val):
            return None
        return float(val)
    return val


# Some IDX tickers (IFRS direct method) use different field names than the standard ones.
# Maps canonical metric name -> list of alternative yfinance field names to try.
METRIC_ALIASES = {
    "Operating Cash Flow": [
        "Cash Flowsfromusedin Operating Activities Direct",
        "Operating Activities",
    ],
    "Free Cash Flow": [
        "Free Cash Flow",  # already canonical, kept for completeness
    ],
}


def _extract_row(df, row_name):
    """Extract a row from a financial statement as a sorted series (oldest first).

    Tries the canonical row_name first, then any known aliases.
    """
    if df is None or df.empty:
        return None
    # Try primary name
    candidates = [row_name] + [a for a in METRIC_ALIASES.get(row_name, []) if a != row_name]
    for name in candidates:
        if name in df.index:
            return df.loc[name].iloc[::-1]
    return None


KEY_METRICS = {
    "income": [
        "Total Revenue", "Gross Profit", "Operating Income",
        "Net Income", "EBITDA", "Basic EPS",
    ],
    "balance": [
        "Total Assets", "Total Debt", "Stockholders Equity",
        "Cash And Cash Equivalents", "Net Receivables",
    ],
    "cashflow": [
        "Operating Cash Flow", "Free Cash Flow", "Capital Expenditure",
    ],
}


def get_trend_analysis(symbol):
    """Analyze YoY trends for key financial metrics.

    Returns:
        dict with trend data per metric category
    """
    financials = get_financials(symbol)
    quarterly = get_quarterly_financials(symbol)
    balance = get_balance_sheet(symbol)
    cashflow = get_cashflow(symbol)

    trends = {"annual": {}, "quarterly": {}}

    # Annual trends
    source_map = {
        "income": financials,
        "balance": balance,
        "cashflow": cashflow,
    }

    for category, metrics in KEY_METRICS.items():
        df = source_map.get(category)
        for metric in metrics:
            series = _extract_row(df, metric)
            if series is not None and len(series) >= 2:
                safe_series = series.map(_safe)
                growth_data = calc_growth_series(safe_series)

                # Calculate CAGR if enough data
                values = [g["value"] for g in growth_data if g["value"] is not None]
                cagr = None
                if len(values) >= 2:
                    cagr = calc_cagr(values[0], values[-1], len(values) - 1)

                trends["annual"][metric] = {
                    "category": category,
                    "data": growth_data,
                    "cagr": round(cagr, 2) if cagr is not None else None,
                }

    # Quarterly trends (income statement only)
    if quarterly is not None and not quarterly.empty:
        for metric in KEY_METRICS["income"]:
            series = _extract_row(quarterly, metric)
            if series is not None and len(series) >= 2:
                safe_series = series.map(_safe)
                growth_data = calc_growth_series(safe_series)
                trends["quarterly"][metric] = {
                    "category": "income",
                    "data": growth_data,
                }

    return trends
