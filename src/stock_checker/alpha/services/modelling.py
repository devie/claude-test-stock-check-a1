"""Modelling service: DCF, scenarios, sensitivity, projections."""

from stock_checker.alpha.services.data_fetcher import get_info, get_cashflow, get_balance_sheet
from stock_checker.alpha.calculations.valuation import (
    calc_dcf, calc_scenario, calc_sensitivity, calc_linear_projection
)
from stock_checker.alpha.services.trends import _safe, _extract_row


def _get_fcf_base(symbol):
    """Extract latest FCF, shares outstanding, and net debt from statements."""
    cashflow = get_cashflow(symbol)
    balance = get_balance_sheet(symbol)
    info = get_info(symbol)

    fcf = None
    if cashflow is not None and "Free Cash Flow" in cashflow.index:
        fcf = _safe(cashflow.loc["Free Cash Flow"].iloc[0])

    shares = info.get("sharesOutstanding")

    # Get debt and cash from balance sheet (info dict is often empty due to 401)
    total_debt = 0
    cash = 0
    if balance is not None and not balance.empty:
        latest_bs = balance.iloc[:, 0]
        td = _safe(latest_bs.get("Total Debt"))
        if td is not None:
            total_debt = td
        c = _safe(latest_bs.get("Cash And Cash Equivalents"))
        if c is not None:
            cash = c

    # Fallback to info dict if balance sheet didn't have data
    if total_debt == 0:
        total_debt = info.get("totalDebt", 0) or 0
    if cash == 0:
        cash = info.get("totalCash", 0) or 0

    net_debt = total_debt - cash
    return fcf, shares, net_debt


def run_dcf(symbol, growth_rate=0.10, terminal_growth=0.03, wacc=0.10,
            projection_years=5, fcf_override=None):
    """Run DCF valuation for a ticker."""
    fcf_base, shares, net_debt = _get_fcf_base(symbol)

    if fcf_override is not None:
        fcf_base = fcf_override

    if fcf_base is None:
        return {"error": "Free Cash Flow data not available for this ticker"}

    info = get_info(symbol)
    current_price = info.get("currentPrice") or info.get("regularMarketPrice")

    result = calc_dcf(fcf_base, growth_rate, terminal_growth, wacc,
                      projection_years, shares, net_debt)

    result["current_price"] = _safe(current_price)
    result["fcf_base"] = fcf_base
    result["shares_outstanding"] = shares
    result["net_debt"] = net_debt

    # Upside/downside
    if "intrinsic_per_share" in result and current_price:
        result["upside_pct"] = round(
            (result["intrinsic_per_share"] - current_price) / current_price * 100, 2
        )

    return result


def run_scenario(symbol, scenarios=None, terminal_growth=0.03, wacc=0.10,
                 projection_years=5):
    """Run bull/base/bear scenario analysis."""
    if scenarios is None:
        scenarios = {"bull": 0.15, "base": 0.10, "bear": 0.05}

    fcf_base, shares, net_debt = _get_fcf_base(symbol)
    if fcf_base is None:
        return {"error": "Free Cash Flow data not available"}

    info = get_info(symbol)
    current_price = info.get("currentPrice") or info.get("regularMarketPrice")

    results = calc_scenario(fcf_base, scenarios, wacc, terminal_growth,
                            projection_years, shares, net_debt)

    return {
        "fcf_base": fcf_base,
        "current_price": _safe(current_price),
        "scenarios": results,
    }


def run_sensitivity(symbol, wacc_range=None, growth_range=None,
                    terminal_growth=0.03, projection_years=5):
    """Run 2D sensitivity analysis."""
    if wacc_range is None:
        wacc_range = [0.08, 0.09, 0.10, 0.11, 0.12]
    if growth_range is None:
        growth_range = [0.05, 0.08, 0.10, 0.12, 0.15]

    fcf_base, shares, net_debt = _get_fcf_base(symbol)
    if fcf_base is None:
        return {"error": "Free Cash Flow data not available"}

    return calc_sensitivity(fcf_base, wacc_range, growth_range,
                            terminal_growth, projection_years, shares, net_debt)


def run_projection(symbol, metric="Total Revenue", periods_ahead=4):
    """Run linear projection on a financial metric."""
    from stock_checker.alpha.services.data_fetcher import get_financials

    # Try income statement first, then cashflow, then balance sheet
    series = None
    for fetcher in [get_financials, get_cashflow, get_balance_sheet]:
        df = fetcher(symbol)
        series = _extract_row(df, metric)
        if series is not None:
            break

    if series is None:
        return {"error": f"Metric '{metric}' not available"}

    values = [_safe(v) for v in series.values]
    labels = [s.strftime("%Y-%m-%d") if hasattr(s, 'strftime') else str(s)
              for s in series.index]

    result = calc_linear_projection(values, periods_ahead)
    result["metric"] = metric
    result["historical_labels"] = labels
    result["historical_values"] = values

    return result
