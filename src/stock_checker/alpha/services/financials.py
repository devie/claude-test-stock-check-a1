"""Financial statement parsing and ratio calculation service."""

import math
import numpy as np
from stock_checker.alpha.services.data_fetcher import (
    get_info, get_financials, get_quarterly_financials,
    get_balance_sheet, get_cashflow,
)
from stock_checker.alpha.calculations.ratios import calc_all_ratios
from stock_checker.alpha.calculations.anomaly import detect_anomalies
from stock_checker.alpha.calculations.growth import calc_yoy_growth


def _safe(val):
    """Convert to JSON-safe value."""
    if val is None:
        return None
    if isinstance(val, (np.integer,)):
        return int(val)
    if isinstance(val, (np.floating, float)):
        if math.isnan(val) or math.isinf(val):
            return None
        return float(val)
    return val


def _df_to_dict(df):
    """Convert a financial statement DataFrame to a dict of {row_label: {date: value}}."""
    if df is None or df.empty:
        return {}
    result = {}
    for row_label in df.index:
        result[row_label] = {}
        for col in df.columns:
            date_str = col.strftime("%Y-%m-%d") if hasattr(col, 'strftime') else str(col)
            result[row_label][date_str] = _safe(df.loc[row_label, col])
    return result


def get_financial_analysis(symbol):
    """Full financial analysis for a single ticker.

    Returns:
        dict with statements, ratios, anomalies
    """
    info = get_info(symbol)
    # Even if info is sparse, proceed if we have financials
    financials = get_financials(symbol)
    if not info and (financials is None or financials.empty):
        raise ValueError(f"No data available for {symbol}")

    quarterly = get_quarterly_financials(symbol)
    balance = get_balance_sheet(symbol)
    cashflow = get_cashflow(symbol)

    # Calculate ratios
    ratios = calc_all_ratios(info, financials, balance)

    # Build anomaly detection data
    anomaly_data = {}
    if financials is not None and not financials.empty:
        try:
            revenues = financials.loc["Total Revenue"] if "Total Revenue" in financials.index else None
            if revenues is not None and len(revenues) >= 2:
                rev_vals = [_safe(v) for v in revenues.values]
                anomaly_data["revenue_growth"] = calc_yoy_growth(rev_vals[0], rev_vals[1])

            net_incomes = financials.loc["Net Income"] if "Net Income" in financials.index else None
            if net_incomes is not None:
                anomaly_data["net_income"] = _safe(net_incomes.iloc[0])
        except (KeyError, IndexError):
            pass

    if cashflow is not None and not cashflow.empty:
        try:
            fcf_row = cashflow.loc["Free Cash Flow"] if "Free Cash Flow" in cashflow.index else None
            if fcf_row is not None:
                anomaly_data["fcf"] = _safe(fcf_row.iloc[0])
        except (KeyError, IndexError):
            pass

    if balance is not None and not balance.empty:
        try:
            receivables = balance.loc.get("Net Receivables")
            if receivables is not None and len(receivables) >= 2:
                rec_vals = [_safe(v) for v in receivables.values]
                anomaly_data["receivables_growth"] = calc_yoy_growth(rec_vals[0], rec_vals[1])
        except (KeyError, IndexError, AttributeError):
            pass

    anomalies = detect_anomalies(anomaly_data)

    # Price summary from info/fast_info
    price_summary = {
        "current_price": _safe(info.get("currentPrice") or info.get("regularMarketPrice")),
        "market_cap": _safe(info.get("marketCap")),
        "52w_high": _safe(info.get("fiftyTwoWeekHigh")),
        "52w_low": _safe(info.get("fiftyTwoWeekLow")),
        "shares_outstanding": _safe(info.get("sharesOutstanding")),
        "currency": info.get("currency", "N/A"),
        "avg_volume": _safe(info.get("averageVolume")),
    }

    # Key financial highlights (latest year)
    highlights = {}
    if financials is not None and not financials.empty:
        latest = financials.iloc[:, 0]
        for key in ["Total Revenue", "Gross Profit", "Operating Income",
                     "Net Income", "EBITDA", "Basic EPS"]:
            if key in latest.index:
                highlights[key] = _safe(latest[key])
    if cashflow is not None and not cashflow.empty:
        cf_latest = cashflow.iloc[:, 0]
        for key in ["Operating Cash Flow", "Free Cash Flow", "Capital Expenditure"]:
            if key in cf_latest.index:
                highlights[key] = _safe(cf_latest[key])

    return {
        "ticker": symbol,
        "name": info.get("longName") or info.get("shortName", symbol),
        "sector": info.get("sector", "N/A"),
        "industry": info.get("industry", "N/A"),
        "price_summary": price_summary,
        "highlights": highlights,
        "ratios": {k: round(v, 2) if v is not None else None for k, v in ratios.items()},
        "income_statement": _df_to_dict(financials),
        "quarterly_income": _df_to_dict(quarterly),
        "balance_sheet": _df_to_dict(balance),
        "cash_flow": _df_to_dict(cashflow),
        "anomalies": anomalies,
    }
