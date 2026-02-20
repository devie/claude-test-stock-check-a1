"""Scoring service: computes Quality, Valuation, Risk, and Composite scores."""

from stock_checker.alpha.services.financials import get_financial_analysis
from stock_checker.alpha.services.trends import get_trend_analysis
from stock_checker.alpha.services.data_fetcher import get_info
from stock_checker.alpha.calculations.scores import (
    calc_quality_score,
    calc_valuation_score,
    calc_risk_score,
    calc_composite_score,
)
from stock_checker.alpha.calculations.industry import detect_industry


def get_scores(symbol):
    """Compute all scores for a ticker.

    Calls get_financial_analysis() + get_trends(), then runs the scoring engine.
    Sector is detected to enable sector-aware risk scoring (e.g. banking DER adjustment).

    Returns:
        dict with quality_score, valuation_score, risk_score, composite_score,
              recommendation, score_details
    """
    fin = get_financial_analysis(symbol)
    trends = get_trend_analysis(symbol)

    ratios = fin.get('ratios', {})

    # Detect sector for context-aware scoring (e.g. banking DER exception)
    sector_key = 'unknown'
    try:
        info = get_info(symbol)
        sector_key = detect_industry(
            info.get('sector', ''),
            info.get('industry', ''),
        )
    except Exception:
        pass

    quality = calc_quality_score(ratios, trends)
    valuation = calc_valuation_score(ratios)
    risk = calc_risk_score(ratios, sector=sector_key)
    composite = calc_composite_score(
        quality['score'],
        valuation['score'],
        risk['score'],
    )

    return {
        'ticker': symbol,
        'quality_score': quality['score'],
        'valuation_score': valuation['score'],
        'risk_score': risk['score'],
        'composite_score': composite['composite_score'],
        'recommendation': composite['recommendation'],
        'score_details': {
            'quality': quality['breakdown'],
            'valuation': valuation['breakdown'],
            'risk': risk['breakdown'],
        },
    }
