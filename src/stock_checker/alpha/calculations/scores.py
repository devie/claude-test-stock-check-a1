"""Composite scoring engine: Quality, Valuation, and Risk scores (0-100)."""


def _norm(v, lo, hi):
    """Normalize v from [lo, hi] range to [0, 100]. Clamps at boundaries."""
    if v is None:
        return None
    if hi == lo:
        return 50.0
    score = (v - lo) / (hi - lo) * 100
    return max(0.0, min(100.0, score))


def _weighted_avg(scores_weights):
    """Compute weighted average ignoring None values.

    Args:
        scores_weights: list of (score, weight) tuples

    Returns:
        float or None
    """
    total_weight = 0.0
    total_score = 0.0
    for score, weight in scores_weights:
        if score is not None:
            total_score += score * weight
            total_weight += weight
    if total_weight == 0:
        return None
    return round(total_score / total_weight, 1)


def calc_quality_score(ratios, trends):
    """Compute Quality Score (0-100) from profitability + growth metrics.

    Metrics (higher = better quality):
      ROE          0-30%     weight 25%
      ROA          0-15%     weight 15%
      NPM          0-30%     weight 20%
      GPM          0-60%     weight 10%
      Revenue CAGR -10-30%   weight 10%
      NI CAGR      -10-30%   weight 10%
      FCF CAGR     -10-30%   weight 10%

    Args:
        ratios: dict from calc_all_ratios (keys: ROE, ROA, NPM, GPM)
        trends: dict from get_trends()['annual'] (keys: 'Total Revenue', 'Net Income', 'Free Cash Flow')

    Returns:
        dict with score and breakdown
    """
    roe = ratios.get('ROE')
    roa = ratios.get('ROA')
    npm = ratios.get('NPM')
    gpm = ratios.get('GPM')

    rev_cagr = None
    ni_cagr = None
    fcf_cagr = None
    if trends:
        annual = trends.get('annual', {})
        if annual.get('Total Revenue') and annual['Total Revenue'].get('cagr') is not None:
            rev_cagr = annual['Total Revenue']['cagr']
        if annual.get('Net Income') and annual['Net Income'].get('cagr') is not None:
            ni_cagr = annual['Net Income']['cagr']
        if annual.get('Free Cash Flow') and annual['Free Cash Flow'].get('cagr') is not None:
            fcf_cagr = annual['Free Cash Flow']['cagr']

    breakdown = {
        'ROE': _norm(roe, 0, 30),
        'ROA': _norm(roa, 0, 15),
        'NPM': _norm(npm, 0, 30),
        'GPM': _norm(gpm, 0, 60),
        'Revenue CAGR': _norm(rev_cagr, -10, 30),
        'NI CAGR': _norm(ni_cagr, -10, 30),
        'FCF CAGR': _norm(fcf_cagr, -10, 30),
    }

    score = _weighted_avg([
        (breakdown['ROE'], 0.25),
        (breakdown['ROA'], 0.15),
        (breakdown['NPM'], 0.20),
        (breakdown['GPM'], 0.10),
        (breakdown['Revenue CAGR'], 0.10),
        (breakdown['NI CAGR'], 0.10),
        (breakdown['FCF CAGR'], 0.10),
    ])

    return {'score': score, 'breakdown': breakdown}


def calc_valuation_score(ratios):
    """Compute Valuation Score (0-100): cheap = high score.

    Metrics:
      PER       40x→0,  5x→100   weight 30%
      PBV       5x→0,   0.5x→100 weight 25%
      EV/EBITDA 20x→0,  4x→100  weight 25%
      PEG       4x→0,   0.5x→100 weight 20%

    Missing metrics use weighted average of available ones.

    Args:
        ratios: dict from calc_all_ratios

    Returns:
        dict with score and breakdown
    """
    per = ratios.get('PER')
    pbv = ratios.get('PBV')
    ev_ebitda = ratios.get('EV/EBITDA')
    peg = ratios.get('PEG')

    # Invert: lower ratio = higher score
    def _norm_inv(v, lo, hi):
        """Normalize inverted: lo = 100, hi = 0."""
        if v is None:
            return None
        # Invert: map hi to 0, lo to 100
        score = (hi - v) / (hi - lo) * 100
        return max(0.0, min(100.0, score))

    breakdown = {
        'PER': _norm_inv(per, 5, 40) if per is not None and per > 0 else None,
        'PBV': _norm_inv(pbv, 0.5, 5) if pbv is not None and pbv > 0 else None,
        'EV/EBITDA': _norm_inv(ev_ebitda, 4, 20) if ev_ebitda is not None and ev_ebitda > 0 else None,
        'PEG': _norm_inv(peg, 0.5, 4) if peg is not None and peg > 0 else None,
    }

    score = _weighted_avg([
        (breakdown['PER'], 0.30),
        (breakdown['PBV'], 0.25),
        (breakdown['EV/EBITDA'], 0.25),
        (breakdown['PEG'], 0.20),
    ])

    return {'score': score, 'breakdown': breakdown}


def calc_risk_score(ratios, sector=None):
    """Compute Risk Score (0-100): low risk = high score.

    Default (non-financial):
      DER          3x→0,   0x→100  weight 40%
      Beta (abs)   3→0,    0→100   weight 30%
      Current Ratio 0→0,  3+→100   weight 30%

    Sector adjustments:
      perbankan:  DER is structural (deposit leverage) — treated as neutral (50),
                  Current Ratio inapplicable for banks; score driven by Beta only.
      Capex-heavy (telekomunikasi, properti_konstruksi, logistik_transportasi):
                  DER tolerance extended to 5x (high leverage is expected/normal).

    Args:
        ratios: dict from calc_all_ratios
        sector: industry_key string for sector-aware adjustments (optional)

    Returns:
        dict with score and breakdown
    """
    _CAPEX_HEAVY = {'telekomunikasi', 'properti_konstruksi', 'logistik_transportasi', 'infrastruktur'}

    der = ratios.get('DER')
    beta = ratios.get('Beta')
    current_ratio = ratios.get('Current Ratio')

    # Beta (abs): 0 = safe (100), 3 = risky (0) — universal
    beta_score = None
    if beta is not None:
        beta_score = max(0.0, min(100.0, (3 - abs(beta)) / 3 * 100))

    if sector == 'perbankan':
        # Banks: deposit leverage is structural, not distress.
        # DER ~8–15x is normal; penalising it is analytically incorrect.
        # Current Ratio is not a meaningful concept for deposit-funded institutions.
        # Score is driven entirely by Beta (market risk).
        der_score = 50.0  # Neutral — structural, not risk signal
        cr_score = None   # Not applicable
        breakdown = {
            'DER': None,   # Marked as not applicable
            'Beta': round(beta_score, 1) if beta_score is not None else None,
            'Current Ratio': None,  # Not applicable
        }
        score = _weighted_avg([(beta_score, 1.0)])
        return {'score': score, 'breakdown': breakdown}

    # Capex-heavy sectors: extended DER tolerance — distress threshold at 5x, not 3x
    der_limit = 5.0 if sector in _CAPEX_HEAVY else 3.0

    der_score = None
    if der is not None:
        der_score = max(0.0, min(100.0, (der_limit - abs(der)) / der_limit * 100))

    # Current Ratio: 0 = risky (0), 3+ = safe (100)
    cr_score = None
    if current_ratio is not None:
        cr_score = max(0.0, min(100.0, current_ratio / 3 * 100))

    breakdown = {
        'DER': round(der_score, 1) if der_score is not None else None,
        'Beta': round(beta_score, 1) if beta_score is not None else None,
        'Current Ratio': round(cr_score, 1) if cr_score is not None else None,
    }

    score = _weighted_avg([
        (der_score, 0.40),
        (beta_score, 0.30),
        (cr_score, 0.30),
    ])

    return {'score': score, 'breakdown': breakdown}


def calc_composite_score(quality_score, valuation_score, risk_score):
    """Compute composite score and auto recommendation.

    composite = 0.35 * quality + 0.35 * valuation + 0.30 * risk

    Recommendations:
      Strong Buy : composite >= 75 AND valuation >= 60
      Buy        : composite >= 60 AND valuation >= 45
      Hold       : composite >= 45
      Avoid      : composite <  45

    Args:
        quality_score: float or None (0-100)
        valuation_score: float or None (0-100)
        risk_score: float or None (0-100)

    Returns:
        dict with composite_score and recommendation
    """
    composite = _weighted_avg([
        (quality_score, 0.35),
        (valuation_score, 0.35),
        (risk_score, 0.30),
    ])

    recommendation = None
    if composite is not None and valuation_score is not None:
        if composite >= 75 and valuation_score >= 60:
            recommendation = 'Strong Buy'
        elif composite >= 60 and valuation_score >= 45:
            recommendation = 'Buy'
        elif composite >= 45:
            recommendation = 'Hold'
        else:
            recommendation = 'Avoid'
    elif composite is not None:
        if composite >= 75:
            recommendation = 'Strong Buy'
        elif composite >= 60:
            recommendation = 'Buy'
        elif composite >= 45:
            recommendation = 'Hold'
        else:
            recommendation = 'Avoid'

    return {
        'composite_score': composite,
        'recommendation': recommendation,
    }
