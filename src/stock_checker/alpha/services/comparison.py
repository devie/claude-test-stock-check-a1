"""Multi-ticker comparison service."""

import math
from stock_checker.alpha.services.data_fetcher import get_info, get_financials, get_balance_sheet, get_cashflow
from stock_checker.alpha.calculations.ratios import calc_all_ratios
from stock_checker.indicators import format_number


METRIC_CATEGORIES = {
    "valuation": ["PER", "PBV", "EV/EBITDA", "PEG"],
    "profitability": ["ROE", "ROA", "NPM", "GPM"],
    "risk": ["Beta", "DER", "Current Ratio"],
    "market": ["Market Cap", "Dividend Yield", "Current Price"],
}


def _safe_val(v):
    if v is None:
        return None
    if isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
        return None
    return v


def compare_tickers(tickers, categories=None):
    """Compare multiple tickers across metric categories.

    Args:
        tickers: list of ticker symbols (max 8)
        categories: list of category names to include (None = all)

    Returns:
        dict with comparison data per ticker
    """
    if len(tickers) > 8:
        raise ValueError("Maximum 8 tickers for comparison")

    if categories is None:
        categories = list(METRIC_CATEGORIES.keys())

    results = {}
    for symbol in tickers:
        try:
            info = get_info(symbol)
            financials = get_financials(symbol)
            balance = get_balance_sheet(symbol)
            cashflow = get_cashflow(symbol)

            if not info and (financials is None or financials.empty):
                results[symbol] = {"error": f"No data for {symbol}"}
                continue

            ratios = calc_all_ratios(info, financials, balance, cashflow)

            ticker_data = {
                "name": info.get("longName") or info.get("shortName", symbol),
                "sector": info.get("sector", "N/A"),
                "metrics": {},
            }

            # Add market data
            ticker_data["metrics"]["Market Cap"] = _safe_val(info.get("marketCap"))
            ticker_data["metrics"]["Current Price"] = _safe_val(
                info.get("currentPrice") or info.get("regularMarketPrice")
            )

            # Add ratios by category
            for cat in categories:
                if cat in METRIC_CATEGORIES:
                    for metric in METRIC_CATEGORIES[cat]:
                        if metric in ratios:
                            ticker_data["metrics"][metric] = _safe_val(ratios[metric])

            results[symbol] = ticker_data
        except Exception as e:
            results[symbol] = {"error": str(e)}

    # Build comparison table structure
    all_metrics = []
    for cat in categories:
        if cat in METRIC_CATEGORIES:
            all_metrics.extend(METRIC_CATEGORIES[cat])

    comparison = {
        "tickers": tickers,
        "categories": categories,
        "metrics": all_metrics,
        "data": results,
    }

    return comparison
