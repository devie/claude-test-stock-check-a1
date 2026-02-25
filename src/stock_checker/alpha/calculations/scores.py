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


# ── Sector-specific quality weights ─────────────────────────────────────────
# Keys: ROE, ROA, NPM, GPM, Revenue CAGR, NI CAGR, FCF CAGR.
# Weights sum to 1.0; zero-weight metrics are computed but excluded from score.
_QUALITY_WEIGHTS = {
    'perbankan': {
        # Banks: spread income + fees; Gross Margin is inapplicable.
        # FCF is not a meaningful concept for deposit-funded lenders.
        # ROE is the primary efficiency signal (driven by leverage + spread).
        'ROE': 0.35, 'ROA': 0.25, 'NPM': 0.25, 'GPM': 0.00,
        'Revenue CAGR': 0.05, 'NI CAGR': 0.10, 'FCF CAGR': 0.00,
    },
    'consumer_goods': {
        # Brand moats and pricing power → Gross Margin is the key quality signal.
        'ROE': 0.20, 'ROA': 0.10, 'NPM': 0.15, 'GPM': 0.25,
        'Revenue CAGR': 0.10, 'NI CAGR': 0.10, 'FCF CAGR': 0.10,
    },
    'teknologi': {
        # Platform/network companies: revenue growth dominates over margin.
        # GPM matters but growth trajectory is the primary quality signal.
        'ROE': 0.15, 'ROA': 0.10, 'NPM': 0.15, 'GPM': 0.15,
        'Revenue CAGR': 0.25, 'NI CAGR': 0.10, 'FCF CAGR': 0.10,
    },
    'energi_pertambangan': {
        # Commodity cycles: FCF is cycle-resilient vs earnings (capex + price-aware).
        # Revenue growth is noisy (driven by commodity prices, not volume alone).
        'ROE': 0.20, 'ROA': 0.15, 'NPM': 0.20, 'GPM': 0.10,
        'Revenue CAGR': 0.05, 'NI CAGR': 0.10, 'FCF CAGR': 0.20,
    },
}

_QUALITY_DEFAULT = {
    'ROE': 0.25, 'ROA': 0.15, 'NPM': 0.20, 'GPM': 0.10,
    'Revenue CAGR': 0.10, 'NI CAGR': 0.10, 'FCF CAGR': 0.10,
}


def calc_quality_score(ratios, trends, sector=None):
    """Compute Quality Score (0-100) from profitability + growth metrics.

    Normalization ranges (universal):
      ROE          0-30%     weight varies by sector
      ROA          0-15%     weight varies by sector
      NPM          0-30%     weight varies by sector
      GPM          0-60%     weight varies by sector (0 for banks)
      Revenue CAGR -10-30%   weight varies by sector
      NI CAGR      -10-30%   weight varies by sector
      FCF CAGR     -10-30%   weight varies by sector (0 for banks)

    Sector-specific weights (see _QUALITY_WEIGHTS):
      perbankan          — GPM/FCF CAGR zeroed; ROE 35%, ROA 25%, NPM 25%
      consumer_goods     — GPM 25% (brand moat signal)
      teknologi          — Revenue CAGR 25% (growth dominates)
      energi_pertambangan — FCF CAGR 20% (cycle-resilient cash generation)
      all others         — default weights

    Args:
        ratios: dict from calc_all_ratios (keys: ROE, ROA, NPM, GPM)
        trends: dict from get_trends() (keys: 'annual' → metric → 'cagr')
        sector: industry_key string for sector-aware weighting (optional)

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

    w = _QUALITY_WEIGHTS.get(sector, _QUALITY_DEFAULT)
    score = _weighted_avg([
        (breakdown['ROE'],          w['ROE']),
        (breakdown['ROA'],          w['ROA']),
        (breakdown['NPM'],          w['NPM']),
        (breakdown['GPM'],          w['GPM']),
        (breakdown['Revenue CAGR'], w['Revenue CAGR']),
        (breakdown['NI CAGR'],      w['NI CAGR']),
        (breakdown['FCF CAGR'],     w['FCF CAGR']),
    ])

    return {'score': score, 'breakdown': breakdown}


def calc_valuation_score(ratios, sector=None):
    """Compute Valuation Score (0-100): cheap = high score.

    Default metrics and weights:
      PER       40x→0,  5x→100   weight 30%
      PBV       5x→0,   0.5x→100 weight 25%
      EV/EBITDA 20x→0,  4x→100  weight 25%
      PEG       4x→0,   0.5x→100 weight 20%

    Sector adjustments:
      perbankan          — PER range 5-20x; PBV range 0.5-5.5x (extended: BBCA ~4.5x is normal premium);
                           EV/EBITDA and PEG excluded (not applicable).
                           Weights: PER 50%, PBV 50%.
      consumer_goods     — EV/EBITDA primary (45%, range 8-25x); PER 35% (10-40x);
                           PBV near-excluded (5%, range 2-20x): brand intangibles inflate PBV;
                           PEG 15%. Reflects FMCG premium-multiple reality.
      telekomunikasi     — EV/EBITDA primary (60%); PER 20%, PEG 15%, PBV 5%.
      energi_pertambangan — EV/EBITDA primary (65%); PER 25%, PBV 10%.
                           PEG excluded: cyclical earnings make forward growth unreliable.
      properti_konstruksi — PBV primary (60%, range 0.3-2.0x); PER 25%, EV/EBITDA 15%.
      teknologi          — P/S (range 3-20x) supplements/replaces PER for pre-profit names.
                           EV/EBITDA range extended to 30x (tech trades at higher multiples).
                           Weights: PER 30%, P/S 30%, EV/EBITDA 20%, PBV 10%, PEG 10%.

    Missing metrics use weighted average of available ones (_weighted_avg auto-rebalances).

    Args:
        ratios: dict from calc_all_ratios (includes 'P/S' for teknologi)
        sector: industry_key string for sector-aware adjustments (optional)

    Returns:
        dict with score and breakdown
    """
    def _norm_inv(v, lo, hi):
        """Normalize inverted: lo → 100, hi → 0."""
        if v is None:
            return None
        score = (hi - v) / (hi - lo) * 100
        return max(0.0, min(100.0, score))

    per = ratios.get('PER')
    pbv = ratios.get('PBV')
    ev_ebitda = ratios.get('EV/EBITDA')
    peg = ratios.get('PEG')
    ps = ratios.get('P/S')

    # ── Banking ────────────────────────────────────────────────────────────
    if sector == 'perbankan':
        # EV/EBITDA not meaningful for deposit-funded institutions.
        # PBV is the primary metric (franchise premium over book value).
        # Tighter PER range: banks in emerging markets rarely exceed 20x.
        # PBV ceiling raised to 5.5x: BBCA regularly trades at 4-5x — that's a
        # quality premium, not a penalisation trigger.
        per_s = _norm_inv(per, 5, 20) if per is not None and per > 0 else None
        pbv_s = _norm_inv(pbv, 0.5, 5.5) if pbv is not None and pbv > 0 else None
        breakdown = {
            'PER': per_s,
            'PBV': pbv_s,
            'EV/EBITDA': None,
            'PEG': None,
        }
        score = _weighted_avg([(per_s, 0.50), (pbv_s, 0.50)])
        return {'score': score, 'breakdown': breakdown}

    # ── Consumer Goods / FMCG ─────────────────────────────────────────────
    if sector == 'consumer_goods':
        # Brand intangibles (trademarks, distribution) are NOT on the balance sheet
        # → PBV is structurally inflated (UNVR 30-50x, ICBP 5-10x) and non-comparable.
        # EV/EBITDA is the global standard for FMCG valuation.
        # Wide PER range (10-40x): quality FMCG commands premium earnings multiples.
        # PBV included at 5% weight with wide range so it never distorts the score.
        per_s = _norm_inv(per,      10, 40) if per      is not None and per      > 0 else None
        pbv_s = _norm_inv(pbv,       2, 20) if pbv      is not None and pbv      > 0 else None
        ev_s  = _norm_inv(ev_ebitda, 8, 25) if ev_ebitda is not None and ev_ebitda > 0 else None
        peg_s = _norm_inv(peg,     0.5,  3) if peg      is not None and peg      > 0 else None
        breakdown = {
            'PER': per_s,
            'PBV': pbv_s,
            'EV/EBITDA': ev_s,
            'PEG': peg_s,
        }
        score = _weighted_avg([
            (per_s, 0.35), (pbv_s, 0.05), (ev_s, 0.45), (peg_s, 0.15),
        ])
        return {'score': score, 'breakdown': breakdown}

    # ── Telco ──────────────────────────────────────────────────────────────
    if sector == 'telekomunikasi':
        # Capex-intensive, high EBITDA margin; EV/EBITDA is the primary metric.
        per_s = _norm_inv(per, 5, 30) if per is not None and per > 0 else None
        pbv_s = _norm_inv(pbv, 0.5, 5) if pbv is not None and pbv > 0 else None
        ev_s = _norm_inv(ev_ebitda, 4, 20) if ev_ebitda is not None and ev_ebitda > 0 else None
        peg_s = _norm_inv(peg, 0.5, 4) if peg is not None and peg > 0 else None
        breakdown = {
            'PER': per_s,
            'PBV': pbv_s,
            'EV/EBITDA': ev_s,
            'PEG': peg_s,
        }
        score = _weighted_avg([
            (per_s, 0.20), (pbv_s, 0.05), (ev_s, 0.60), (peg_s, 0.15),
        ])
        return {'score': score, 'breakdown': breakdown}

    # ── Mining / Energy ────────────────────────────────────────────────────
    if sector == 'energi_pertambangan':
        # Commodity cycles mean EV/EBITDA is the most cycle-adjusted metric.
        # PEG excluded: forward earnings estimates are notoriously unreliable for
        # cyclical commodities — a "low PEG" at cycle peak is meaningless.
        per_s = _norm_inv(per, 5, 30) if per is not None and per > 0 else None
        pbv_s = _norm_inv(pbv, 0.5, 5) if pbv is not None and pbv > 0 else None
        ev_s  = _norm_inv(ev_ebitda, 4, 20) if ev_ebitda is not None and ev_ebitda > 0 else None
        breakdown = {
            'PER': per_s,
            'PBV': pbv_s,
            'EV/EBITDA': ev_s,
            'PEG': None,
        }
        score = _weighted_avg([
            (per_s, 0.25), (pbv_s, 0.10), (ev_s, 0.65),
        ])
        return {'score': score, 'breakdown': breakdown}

    # ── Property / Construction ────────────────────────────────────────────
    if sector == 'properti_konstruksi':
        # Land/building assets = book value. PBV is the anchor metric.
        # Tighter PBV range: IDX property stocks rarely trade above 2x book.
        per_s = _norm_inv(per, 5, 30) if per is not None and per > 0 else None
        pbv_s = _norm_inv(pbv, 0.3, 2.0) if pbv is not None and pbv > 0 else None
        ev_s = _norm_inv(ev_ebitda, 4, 20) if ev_ebitda is not None and ev_ebitda > 0 else None
        breakdown = {
            'PER': per_s,
            'PBV': pbv_s,
            'EV/EBITDA': ev_s,
            'PEG': None,
        }
        score = _weighted_avg([
            (per_s, 0.25), (pbv_s, 0.60), (ev_s, 0.15),
        ])
        return {'score': score, 'breakdown': breakdown}

    # ── Technology ────────────────────────────────────────────────────────
    if sector == 'teknologi':
        # P/S supplements PER for pre-profit names (GOTO, BUKA).
        # Extended EV/EBITDA range (30x): tech companies trade at higher multiples.
        per_s = _norm_inv(per, 5, 40) if per is not None and per > 0 else None
        pbv_s = _norm_inv(pbv, 0.5, 5) if pbv is not None and pbv > 0 else None
        ev_s = _norm_inv(ev_ebitda, 4, 30) if ev_ebitda is not None and ev_ebitda > 0 else None
        peg_s = _norm_inv(peg, 0.5, 4) if peg is not None and peg > 0 else None
        ps_s = _norm_inv(ps, 3, 20) if ps is not None and ps > 0 else None
        breakdown = {
            'PER': per_s,
            'PBV': pbv_s,
            'EV/EBITDA': ev_s,
            'PEG': peg_s,
            'P/S': ps_s,
        }
        score = _weighted_avg([
            (per_s, 0.30), (pbv_s, 0.10), (ev_s, 0.20), (peg_s, 0.10), (ps_s, 0.30),
        ])
        return {'score': score, 'breakdown': breakdown}

    # ── Default ────────────────────────────────────────────────────────────
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
    _CAPEX_HEAVY  = {'telekomunikasi', 'properti_konstruksi', 'logistik_transportasi', 'infrastruktur'}
    # FMCG companies like UNVR run high DER by design (aggressive dividend → low equity),
    # not financial distress. 4x tolerance avoids unfairly penalising them.
    _MODERATE_DER = {'consumer_goods', 'healthcare'}

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
        breakdown = {
            'DER': None,   # Marked as not applicable
            'Beta': round(beta_score, 1) if beta_score is not None else None,
            'Current Ratio': None,  # Not applicable
        }
        score = _weighted_avg([(beta_score, 1.0)])
        return {'score': score, 'breakdown': breakdown}

    # DER tolerance by sector:
    #   capex-heavy (telco, property): 5x — structural high leverage
    #   consumer_goods / healthcare:   4x — high DER from dividends, not distress
    #   all others:                    3x — standard
    der_limit = 5.0 if sector in _CAPEX_HEAVY else (4.0 if sector in _MODERATE_DER else 3.0)

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
