"""Valuation models: DCF, scenario analysis, sensitivity matrix."""

import math


def calc_dcf(fcf_base, growth_rate, terminal_growth, wacc, projection_years=5,
             shares_outstanding=None, net_debt=0):
    """Discounted Cash Flow valuation.

    Args:
        fcf_base: Base free cash flow (latest year)
        growth_rate: Annual FCF growth rate (decimal, e.g. 0.10 for 10%)
        terminal_growth: Terminal/perpetuity growth rate (decimal)
        wacc: Weighted average cost of capital (decimal)
        projection_years: Number of years to project
        shares_outstanding: For per-share value calculation
        net_debt: Total debt minus cash (subtracted from enterprise value)

    Returns:
        dict with projected FCFs, PV, terminal value, enterprise value, equity value
    """
    if fcf_base is None or wacc is None or wacc <= terminal_growth:
        return {"error": "Invalid inputs: check FCF, WACC, and terminal growth rate"}

    projected_fcf = []
    pv_fcf = []

    for year in range(1, projection_years + 1):
        fcf = fcf_base * ((1 + growth_rate) ** year)
        pv = fcf / ((1 + wacc) ** year)
        projected_fcf.append(round(fcf, 2))
        pv_fcf.append(round(pv, 2))

    # Terminal value (Gordon Growth)
    terminal_fcf = projected_fcf[-1] * (1 + terminal_growth)
    terminal_value = terminal_fcf / (wacc - terminal_growth)
    pv_terminal = terminal_value / ((1 + wacc) ** projection_years)

    enterprise_value = sum(pv_fcf) + pv_terminal
    equity_value = enterprise_value - net_debt

    result = {
        "projected_fcf": projected_fcf,
        "pv_fcf": pv_fcf,
        "sum_pv_fcf": round(sum(pv_fcf), 2),
        "terminal_value": round(terminal_value, 2),
        "pv_terminal": round(pv_terminal, 2),
        "enterprise_value": round(enterprise_value, 2),
        "equity_value": round(equity_value, 2),
    }

    if shares_outstanding and shares_outstanding > 0:
        result["intrinsic_per_share"] = round(equity_value / shares_outstanding, 2)

    return result


def calc_scenario(fcf_base, scenarios, wacc, terminal_growth, projection_years=5,
                  shares_outstanding=None, net_debt=0):
    """Run DCF for bull/base/bear scenarios.

    Args:
        fcf_base: Base free cash flow
        scenarios: dict like {"bull": 0.15, "base": 0.10, "bear": 0.05}
        wacc, terminal_growth, projection_years, shares_outstanding, net_debt: same as calc_dcf

    Returns:
        dict of scenario_name -> DCF result
    """
    results = {}
    for name, growth in scenarios.items():
        results[name] = calc_dcf(
            fcf_base, growth, terminal_growth, wacc,
            projection_years, shares_outstanding, net_debt
        )
    return results


def calc_sensitivity(fcf_base, wacc_range, growth_range, terminal_growth,
                     projection_years=5, shares_outstanding=None, net_debt=0):
    """2D sensitivity matrix: WACC vs Growth Rate.

    Args:
        fcf_base: Base free cash flow
        wacc_range: list of WACC values (decimal)
        growth_range: list of growth rate values (decimal)
        terminal_growth, projection_years, shares_outstanding, net_debt: same as calc_dcf

    Returns:
        dict with wacc_labels, growth_labels, and matrix (2D list of intrinsic values)
    """
    matrix = []
    for wacc in wacc_range:
        row = []
        for growth in growth_range:
            result = calc_dcf(
                fcf_base, growth, terminal_growth, wacc,
                projection_years, shares_outstanding, net_debt
            )
            if "error" in result:
                row.append(None)
            elif "intrinsic_per_share" in result:
                row.append(result["intrinsic_per_share"])
            else:
                row.append(result["equity_value"])
        matrix.append(row)

    return {
        "wacc_labels": [f"{w*100:.1f}%" for w in wacc_range],
        "growth_labels": [f"{g*100:.1f}%" for g in growth_range],
        "matrix": matrix,
    }


def calc_pbv(roe, book_value_per_share, cost_of_equity=0.10, terminal_growth=0.05):
    """PBV (Justified Price-to-Book) valuation model. Best for banks/financials.

    justified_pbv = (ROE - g) / (COE - g)
    intrinsic     = justified_pbv * book_value_per_share

    Args:
        roe: Return on Equity as decimal (e.g. 0.18 for 18%)
        book_value_per_share: Book value per share (currency units)
        cost_of_equity: Cost of equity as decimal (default 10%)
        terminal_growth: Terminal growth rate as decimal (default 5%)

    Returns:
        dict with justified_pbv and intrinsic_per_share
    """
    if roe is None or book_value_per_share is None:
        return {"error": "ROE and book value per share are required"}
    if cost_of_equity <= terminal_growth:
        return {"error": "Cost of equity must be greater than terminal growth rate"}
    if book_value_per_share <= 0:
        return {"error": "Book value per share must be positive"}

    justified_pbv = (roe - terminal_growth) / (cost_of_equity - terminal_growth)
    intrinsic = justified_pbv * book_value_per_share

    return {
        "justified_pbv": round(justified_pbv, 4),
        "intrinsic_per_share": round(intrinsic, 2),
        "roe_used": round(roe * 100, 2),
        "cost_of_equity": round(cost_of_equity * 100, 2),
        "terminal_growth": round(terminal_growth * 100, 2),
        "book_value_per_share": round(book_value_per_share, 2),
    }


def calc_ddm(last_dividend, growth_rate=0.05, cost_of_equity=0.10):
    """Gordon Growth Model / Dividend Discount Model (DDM).

    D1 = last_dividend * (1 + g)
    intrinsic = D1 / (COE - g)

    Args:
        last_dividend: Most recent annual dividend per share
        growth_rate: Expected dividend growth rate (decimal)
        cost_of_equity: Required rate of return (decimal)

    Returns:
        dict with D1 and intrinsic_per_share, or error if no dividend
    """
    if last_dividend is None or last_dividend <= 0:
        return {"error": "This stock does not pay dividends — DDM not applicable"}
    if cost_of_equity <= growth_rate:
        return {"error": "Cost of equity must be greater than growth rate"}

    d1 = last_dividend * (1 + growth_rate)
    intrinsic = d1 / (cost_of_equity - growth_rate)

    return {
        "last_dividend": round(last_dividend, 4),
        "d1": round(d1, 4),
        "intrinsic_per_share": round(intrinsic, 2),
        "growth_rate": round(growth_rate * 100, 2),
        "cost_of_equity": round(cost_of_equity * 100, 2),
    }


def calc_roe_sustainable_growth(roe, payout_ratio, eps, cost_of_equity=0.10):
    """ROE Sustainable Growth Model.

    sustainable_g      = ROE * retention_ratio
    retention_ratio    = 1 - payout_ratio
    intrinsic_per_share = EPS * (1 + g) / (COE - g)

    Args:
        roe: Return on Equity as decimal
        payout_ratio: Dividend payout ratio as decimal (0-1)
        eps: Earnings per share (currency units)
        cost_of_equity: Required rate of return (decimal)

    Returns:
        dict with sustainable_g, retention_ratio, and intrinsic_per_share
    """
    if roe is None or eps is None:
        return {"error": "ROE and EPS are required"}
    if payout_ratio is None:
        payout_ratio = 0.0
    if not (0 <= payout_ratio <= 1):
        payout_ratio = max(0.0, min(1.0, payout_ratio))

    retention_ratio = 1 - payout_ratio
    sustainable_g = roe * retention_ratio

    if cost_of_equity <= sustainable_g:
        return {"error": f"Sustainable growth ({sustainable_g*100:.1f}%) >= cost of equity — model not valid"}

    intrinsic = eps * (1 + sustainable_g) / (cost_of_equity - sustainable_g)

    return {
        "sustainable_g": round(sustainable_g * 100, 2),
        "retention_ratio": round(retention_ratio * 100, 2),
        "payout_ratio": round(payout_ratio * 100, 2),
        "roe_used": round(roe * 100, 2),
        "eps": round(eps, 4),
        "intrinsic_per_share": round(intrinsic, 2),
        "cost_of_equity": round(cost_of_equity * 100, 2),
    }


def calc_linear_projection(values, periods_ahead=4):
    """Simple linear regression projection with confidence bands.

    Args:
        values: list of numeric values (historical, oldest first)
        periods_ahead: number of periods to project

    Returns:
        dict with historical fit, projections, and confidence interval
    """
    n = len(values)
    if n < 2:
        return {"error": "Need at least 2 data points"}

    # Filter out None values
    clean = [(i, v) for i, v in enumerate(values) if v is not None and math.isfinite(v)]
    if len(clean) < 2:
        return {"error": "Need at least 2 valid data points"}

    x_vals = [c[0] for c in clean]
    y_vals = [c[1] for c in clean]

    # Simple linear regression
    n_pts = len(clean)
    sum_x = sum(x_vals)
    sum_y = sum(y_vals)
    sum_xy = sum(x * y for x, y in zip(x_vals, y_vals))
    sum_x2 = sum(x * x for x in x_vals)

    denom = n_pts * sum_x2 - sum_x * sum_x
    if denom == 0:
        return {"error": "Cannot fit line (zero variance in x)"}

    slope = (n_pts * sum_xy - sum_x * sum_y) / denom
    intercept = (sum_y - slope * sum_x) / n_pts

    # Residual standard error
    residuals = [y - (slope * x + intercept) for x, y in zip(x_vals, y_vals)]
    if n_pts > 2:
        se = math.sqrt(sum(r * r for r in residuals) / (n_pts - 2))
    else:
        se = 0

    # Historical fit
    fitted = [round(slope * i + intercept, 2) for i in range(n)]

    # Projections
    projections = []
    for i in range(n, n + periods_ahead):
        val = slope * i + intercept
        projections.append({
            "period_index": i,
            "value": round(val, 2),
            "upper": round(val + 1.96 * se, 2),
            "lower": round(val - 1.96 * se, 2),
        })

    return {
        "slope": round(slope, 4),
        "intercept": round(intercept, 2),
        "r_squared": round(1 - sum(r*r for r in residuals) / max(sum((y - sum_y/n_pts)**2 for y in y_vals), 1e-10), 4),
        "fitted": fitted,
        "projections": projections,
    }
