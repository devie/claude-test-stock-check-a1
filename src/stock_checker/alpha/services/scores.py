"""Scoring service: computes Quality, Valuation, Risk, and Composite scores."""

from stock_checker.alpha.services.financials import get_financial_analysis
from stock_checker.alpha.services.trends import get_trend_analysis
from stock_checker.alpha.calculations.scores import (
    calc_quality_score,
    calc_valuation_score,
    calc_risk_score,
    calc_composite_score,
)


def get_scores(symbol):
    """Compute all scores for a ticker.

    Calls get_financial_analysis() + get_trends(), then runs the scoring engine.

    Returns:
        dict with quality_score, valuation_score, risk_score, composite_score,
              recommendation, score_details
    """
    fin = get_financial_analysis(symbol)
    trends = get_trend_analysis(symbol)

    ratios = fin.get('ratios', {})

    quality = calc_quality_score(ratios, trends)
    valuation = calc_valuation_score(ratios)
    risk = calc_risk_score(ratios)
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
