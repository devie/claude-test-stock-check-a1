"""Financial ratio calculations."""

import math


def safe_div(a, b):
    """Safe division returning None if divisor is zero/None or result is non-finite."""
    if a is None or b is None or b == 0:
        return None
    result = a / b
    if not math.isfinite(result):
        return None
    return result


def calc_per(price, eps):
    """Price to Earnings Ratio."""
    return safe_div(price, eps)


def calc_pbv(price, bvps):
    """Price to Book Value."""
    return safe_div(price, bvps)


def calc_roe(net_income, equity):
    """Return on Equity."""
    r = safe_div(net_income, equity)
    return r * 100 if r is not None else None


def calc_roa(net_income, total_assets):
    """Return on Assets."""
    r = safe_div(net_income, total_assets)
    return r * 100 if r is not None else None


def calc_npm(net_income, revenue):
    """Net Profit Margin (%)."""
    r = safe_div(net_income, revenue)
    return r * 100 if r is not None else None


def calc_gpm(gross_profit, revenue):
    """Gross Profit Margin (%)."""
    r = safe_div(gross_profit, revenue)
    return r * 100 if r is not None else None


def calc_der(total_debt, equity):
    """Debt to Equity Ratio."""
    return safe_div(total_debt, equity)


def calc_current_ratio(current_assets, current_liabilities):
    """Current Ratio."""
    return safe_div(current_assets, current_liabilities)


def calc_interest_coverage(ebit, interest_expense):
    """Interest Coverage Ratio."""
    if interest_expense is not None:
        interest_expense = abs(interest_expense)
    return safe_div(ebit, interest_expense)


def calc_ev_ebitda(market_cap, total_debt, cash, ebitda):
    """EV/EBITDA ratio."""
    if market_cap is None or ebitda is None:
        return None
    ev = market_cap + (total_debt or 0) - (cash or 0)
    return safe_div(ev, ebitda)


def calc_peg(per, earnings_growth):
    """PEG Ratio."""
    if earnings_growth is not None and earnings_growth != 0:
        return safe_div(per, earnings_growth * 100)
    return None


def calc_all_ratios(info, financials=None, balance=None):
    """Calculate all ratios from yfinance data.

    Args:
        info: dict from ticker.info
        financials: income statement DataFrame (optional, for direct calc)
        balance: balance sheet DataFrame (optional, for direct calc)

    Returns:
        dict of ratio name -> value (None if unavailable)
    """
    price = info.get("currentPrice") or info.get("regularMarketPrice")
    eps = info.get("trailingEps")
    bvps = info.get("bookValue")
    market_cap = info.get("marketCap")

    ratios = {
        "PER": calc_per(price, eps),
        "PBV": calc_pbv(price, bvps),
        "ROE": info.get("returnOnEquity", None),
        "ROA": info.get("returnOnAssets", None),
        "NPM": None,
        "GPM": None,
        "DER": info.get("debtToEquity", None),
        "Current Ratio": info.get("currentRatio", None),
        "EV/EBITDA": info.get("enterpriseToEbitda", None),
        "PEG": info.get("pegRatio", None),
        "Beta": info.get("beta", None),
        "Dividend Yield": info.get("dividendYield", None),
    }

    # Convert ROE/ROA from decimal to percentage if they're small
    for key in ("ROE", "ROA"):
        v = ratios[key]
        if v is not None and abs(v) < 1:
            ratios[key] = v * 100

    # Convert dividend yield to percentage
    if ratios["Dividend Yield"] is not None and ratios["Dividend Yield"] < 1:
        ratios["Dividend Yield"] = ratios["Dividend Yield"] * 100

    # Calculate NPM/GPM from financials if available
    if financials is not None and not financials.empty:
        try:
            latest = financials.iloc[:, 0]
            revenue = latest.get("Total Revenue")
            net_income = latest.get("Net Income")
            gross_profit = latest.get("Gross Profit")
            ratios["NPM"] = calc_npm(net_income, revenue)
            ratios["GPM"] = calc_gpm(gross_profit, revenue)
        except (IndexError, KeyError):
            pass

    # DER from balance sheet if not in info
    if ratios["DER"] is None and balance is not None and not balance.empty:
        try:
            latest_bs = balance.iloc[:, 0]
            total_debt = latest_bs.get("Total Debt")
            equity = latest_bs.get("Stockholders Equity") or latest_bs.get("Total Stockholders Equity")
            ratios["DER"] = calc_der(total_debt, equity)
        except (IndexError, KeyError):
            pass

    return ratios
