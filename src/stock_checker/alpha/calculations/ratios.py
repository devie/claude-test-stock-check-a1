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


def _safe(val):
    """Return None for NaN/Inf, else the value."""
    if val is None:
        return None
    try:
        if math.isnan(val) or math.isinf(val):
            return None
    except (TypeError, ValueError):
        pass
    return val


def calc_per(price, eps):
    """Price to Earnings Ratio."""
    return safe_div(price, eps)


def calc_pbv(price, bvps):
    """Price to Book Value."""
    return safe_div(price, bvps)


def calc_roe(net_income, equity):
    """Return on Equity (%)."""
    r = safe_div(net_income, equity)
    return r * 100 if r is not None else None


def calc_roa(net_income, total_assets):
    """Return on Assets (%)."""
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
    if per is None or earnings_growth is None or earnings_growth == 0:
        return None
    return safe_div(per, earnings_growth)


def calc_all_ratios(info, financials=None, balance=None, cashflow=None):
    """Calculate all ratios from financial statements + fast_info.

    Strategy: Always compute from statements first, fall back to info dict.
    This handles the yfinance 401 auth issue where info is empty but
    statements are available.

    Args:
        info: dict from ticker.info / fast_info merge
        financials: income statement DataFrame
        balance: balance sheet DataFrame
        cashflow: cash flow statement DataFrame

    Returns:
        dict of ratio name -> value (None if unavailable)
    """
    price = _safe(info.get("currentPrice") or info.get("regularMarketPrice"))
    market_cap = _safe(info.get("marketCap"))
    shares = _safe(info.get("sharesOutstanding"))

    # Extract values from financial statements
    revenue = net_income = gross_profit = eps = ebit = ebitda = None
    equity = total_assets = total_debt = current_assets = current_liab = cash = None

    if financials is not None and not financials.empty:
        try:
            latest = financials.iloc[:, 0]
            revenue = _safe(latest.get("Total Revenue"))
            net_income = _safe(latest.get("Net Income"))
            gross_profit = _safe(latest.get("Gross Profit"))
            eps = _safe(latest.get("Basic EPS") or latest.get("Diluted EPS"))
            ebit = _safe(latest.get("EBIT"))
            ebitda = _safe(latest.get("EBITDA"))
        except (IndexError, KeyError):
            pass

    if balance is not None and not balance.empty:
        try:
            latest_bs = balance.iloc[:, 0]
            equity = _safe(latest_bs.get("Stockholders Equity") or
                           latest_bs.get("Total Stockholders Equity"))
            total_assets = _safe(latest_bs.get("Total Assets"))
            total_debt = _safe(latest_bs.get("Total Debt"))
            current_assets = _safe(latest_bs.get("Current Assets"))
            current_liab = _safe(latest_bs.get("Current Liabilities"))
            cash = _safe(latest_bs.get("Cash And Cash Equivalents"))
        except (IndexError, KeyError):
            pass

    # Compute BVPS from equity + shares
    bvps = safe_div(equity, shares) if equity and shares else None

    # Compute EPS growth for PEG (need 2 years of EPS)
    eps_growth = None
    if financials is not None and financials.shape[1] >= 2:
        try:
            eps_curr = _safe(financials.iloc[:, 0].get("Basic EPS"))
            eps_prev = _safe(financials.iloc[:, 1].get("Basic EPS"))
            if eps_curr and eps_prev and eps_prev != 0:
                eps_growth = ((eps_curr - eps_prev) / abs(eps_prev)) * 100
        except (IndexError, KeyError):
            pass

    # Calculate all ratios from statements
    per = calc_per(price, eps)

    ratios = {
        "PER": per,
        "PBV": calc_pbv(price, bvps),
        "ROE": calc_roe(net_income, equity),
        "ROA": calc_roa(net_income, total_assets),
        "NPM": calc_npm(net_income, revenue),
        "GPM": calc_gpm(gross_profit, revenue),
        "DER": calc_der(total_debt, equity),
        "Current Ratio": calc_current_ratio(current_assets, current_liab),
        "EV/EBITDA": calc_ev_ebitda(market_cap, total_debt, cash, ebitda),
        "PEG": calc_peg(per, eps_growth) if per and eps_growth else None,
        "Beta": _safe(info.get("beta")),
        "Dividend Yield": _safe(info.get("dividendYield")),
        "P/S": _safe(info.get("priceToSalesTrailing12Months")),
    }

    # Fall back to info values if our calculation returned None
    fallback_map = {
        "PER": "trailingPE",
        "PBV": "priceToBook",
        "ROE": "returnOnEquity",
        "ROA": "returnOnAssets",
        "DER": "debtToEquity",
        "Current Ratio": "currentRatio",
        "EV/EBITDA": "enterpriseToEbitda",
        "PEG": "pegRatio",
    }
    for ratio_key, info_key in fallback_map.items():
        if ratios[ratio_key] is None:
            v = _safe(info.get(info_key))
            if v is not None:
                # Convert ROE/ROA from decimal if needed
                if ratio_key in ("ROE", "ROA") and abs(v) < 1:
                    v = v * 100
                ratios[ratio_key] = v

    # Convert dividend yield to percentage if decimal
    if ratios["Dividend Yield"] is not None and ratios["Dividend Yield"] < 1:
        ratios["Dividend Yield"] = ratios["Dividend Yield"] * 100

    return ratios
