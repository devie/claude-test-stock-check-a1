"""Anomaly detection for financial data."""

import math


def z_score_check(values, threshold=2.0):
    """Flag values that deviate more than threshold standard deviations from mean.

    Args:
        values: list of (label, value) tuples
        threshold: z-score threshold (default 2.0)

    Returns:
        list of anomaly dicts with label, value, z_score, direction
    """
    clean = [(label, v) for label, v in values if v is not None and math.isfinite(v)]
    if len(clean) < 3:
        return []

    nums = [v for _, v in clean]
    mean = sum(nums) / len(nums)
    variance = sum((x - mean) ** 2 for x in nums) / len(nums)
    if variance == 0:
        return []
    std = math.sqrt(variance)

    anomalies = []
    for label, v in clean:
        z = (v - mean) / std
        if abs(z) >= threshold:
            anomalies.append({
                "label": str(label),
                "value": round(v, 2),
                "z_score": round(z, 2),
                "direction": "high" if z > 0 else "low",
            })

    return anomalies


def check_receivables_vs_revenue(revenue_growth, receivables_growth):
    """Flag if receivables growing much faster than revenue (potential quality issue).

    Returns anomaly dict or None.
    """
    if revenue_growth is None or receivables_growth is None:
        return None
    if receivables_growth > revenue_growth + 15:
        return {
            "type": "receivables_growth",
            "message": f"Receivables growth ({receivables_growth:.1f}%) significantly exceeds "
                       f"revenue growth ({revenue_growth:.1f}%)",
            "severity": "warning",
        }
    return None


def check_fcf_vs_net_income(fcf, net_income):
    """Flag persistent divergence between FCF and net income.

    Returns anomaly dict or None.
    """
    if fcf is None or net_income is None or net_income == 0:
        return None
    ratio = fcf / net_income
    if ratio < 0.5:
        return {
            "type": "fcf_divergence",
            "message": f"Free cash flow ({fcf:,.0f}) is significantly below "
                       f"net income ({net_income:,.0f}), ratio={ratio:.2f}",
            "severity": "warning",
        }
    if ratio < 0:
        return {
            "type": "fcf_negative",
            "message": f"Free cash flow is negative ({fcf:,.0f}) despite "
                       f"positive net income ({net_income:,.0f})",
            "severity": "critical",
        }
    return None


def detect_anomalies(financials_data):
    """Run all anomaly detection checks on financial data.

    Args:
        financials_data: dict with keys like 'revenue_series', 'receivables_series',
                        'fcf', 'net_income', 'ratio_history'

    Returns:
        list of anomaly dicts
    """
    anomalies = []

    # Z-score check on ratio history
    ratio_history = financials_data.get("ratio_history", [])
    if ratio_history:
        zscore_anomalies = z_score_check(ratio_history)
        for a in zscore_anomalies:
            a["type"] = "z_score"
            a["severity"] = "info"
        anomalies.extend(zscore_anomalies)

    # Receivables vs revenue
    rev_growth = financials_data.get("revenue_growth")
    rec_growth = financials_data.get("receivables_growth")
    check = check_receivables_vs_revenue(rev_growth, rec_growth)
    if check:
        anomalies.append(check)

    # FCF vs net income
    fcf = financials_data.get("fcf")
    ni = financials_data.get("net_income")
    check = check_fcf_vs_net_income(fcf, ni)
    if check:
        anomalies.append(check)

    return anomalies
