"""Growth calculation functions."""

import math


def calc_yoy_growth(current, previous):
    """Year-over-Year growth rate (%)."""
    if current is None or previous is None or previous == 0:
        return None
    result = ((current - previous) / abs(previous)) * 100
    if not math.isfinite(result):
        return None
    return result


def calc_qoq_growth(current, previous):
    """Quarter-over-Quarter growth rate (%). Same formula as YoY."""
    return calc_yoy_growth(current, previous)


def calc_cagr(start_value, end_value, years):
    """Compound Annual Growth Rate (%)."""
    if start_value is None or end_value is None or years is None or years <= 0:
        return None
    if start_value <= 0 or end_value <= 0:
        return None
    try:
        result = ((end_value / start_value) ** (1 / years) - 1) * 100
        if not math.isfinite(result):
            return None
        return result
    except (ValueError, ZeroDivisionError):
        return None


def calc_growth_series(series):
    """Calculate period-over-period growth rates for a pandas Series.

    Args:
        series: pandas Series with values ordered oldest-to-newest

    Returns:
        list of dicts with {period, value, growth_pct}
    """
    results = []
    values = list(series.items()) if hasattr(series, 'items') else list(enumerate(series))

    for i, (period, value) in enumerate(values):
        growth = None
        if i > 0:
            prev_value = values[i - 1][1]
            growth = calc_yoy_growth(value, prev_value)

        period_str = str(period)
        if hasattr(period, 'strftime'):
            period_str = period.strftime("%Y-%m-%d")

        results.append({
            "period": period_str,
            "value": value if value is not None and math.isfinite(value) else None,
            "growth_pct": round(growth, 2) if growth is not None else None,
        })

    return results
