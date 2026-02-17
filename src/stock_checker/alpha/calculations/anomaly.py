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


def check_margin_decline(current_npm, previous_npm):
    """Flag significant margin decline."""
    if current_npm is None or previous_npm is None:
        return None
    decline = previous_npm - current_npm
    if decline > 5:
        return {
            "type": "margin_decline",
            "message": f"Net profit margin declined {decline:.1f}pp "
                       f"(from {previous_npm:.1f}% to {current_npm:.1f}%)",
            "severity": "warning",
        }
    return None


def check_debt_ratio(der):
    """Flag high debt-to-equity ratio."""
    if der is None:
        return None
    if der > 2.0:
        return {
            "type": "high_leverage",
            "message": f"High debt-to-equity ratio: {der:.2f}x (threshold: 2.0x)",
            "severity": "warning" if der < 3.0 else "critical",
        }
    return None


def check_revenue_decline(revenue_growth):
    """Flag significant revenue decline."""
    if revenue_growth is None:
        return None
    if revenue_growth < -10:
        return {
            "type": "revenue_decline",
            "message": f"Revenue declined {revenue_growth:.1f}% year-over-year",
            "severity": "warning" if revenue_growth > -20 else "critical",
        }
    return None


def detect_anomalies(financials_data):
    """Run all anomaly detection checks on financial data.

    Args:
        financials_data: dict with keys like 'revenue_growth', 'receivables_growth',
                        'fcf', 'net_income', 'ratio_history', 'current_npm',
                        'previous_npm', 'der'

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
    check = check_receivables_vs_revenue(
        financials_data.get("revenue_growth"),
        financials_data.get("receivables_growth"),
    )
    if check:
        anomalies.append(check)

    # FCF vs net income
    check = check_fcf_vs_net_income(
        financials_data.get("fcf"),
        financials_data.get("net_income"),
    )
    if check:
        anomalies.append(check)

    # Margin decline
    check = check_margin_decline(
        financials_data.get("current_npm"),
        financials_data.get("previous_npm"),
    )
    if check:
        anomalies.append(check)

    # High leverage
    check = check_debt_ratio(financials_data.get("der"))
    if check:
        anomalies.append(check)

    # Revenue decline
    check = check_revenue_decline(financials_data.get("revenue_growth"))
    if check:
        anomalies.append(check)

    return anomalies
