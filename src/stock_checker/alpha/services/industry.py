"""Industry analysis service."""

import yfinance as yf

from stock_checker.alpha.services.financials import get_financial_analysis
from stock_checker.alpha.calculations.industry import (
    detect_industry,
    get_industry_config,
    calc_specific_ratios,
    detect_valuation_zone,
)


def get_industry_context(symbol: str) -> dict:
    """Return full industry analysis context for a ticker."""
    fin = get_financial_analysis(symbol)

    sector        = fin.get('sector', '')  or ''
    industry_name = fin.get('industry', '') or ''
    currency      = (fin.get('price_summary') or {}).get('currency', 'IDR')

    # Fetch raw info for extra fields not surfaced by get_financial_analysis
    # (totalDebt, totalAssets, netInterestMargin, revenueGrowth, etc.)
    try:
        info = yf.Ticker(symbol).info or {}
    except Exception:
        info = {}

    industry_key = detect_industry(sector, industry_name)
    config       = get_industry_config(industry_key)

    specific_ratios = calc_specific_ratios(
        industry_key,
        fin.get('ratios', {}),
        fin.get('highlights', {}),
        fin.get('price_summary', {}),
        info,
    )

    valuation = detect_valuation_zone(specific_ratios, config)

    # Select peers: IDX list for .JK tickers, US list otherwise; exclude self
    is_idx   = symbol.upper().endswith('.JK')
    all_peers = config.get('peers_IDX' if is_idx else 'peers_US', [])
    peers     = [p for p in all_peers if p.upper() != symbol.upper()][:2]

    return {
        'ticker':          symbol,
        'industry_key':    industry_key,
        'label':           config['label'],
        'icon':            config['icon'],
        'sector':          sector,
        'industry':        industry_name,
        'specific_ratios': specific_ratios,
        'valuation':       valuation,
        'peers': {
            'tickers': peers,
            'metrics': config.get('peer_metrics', []),
        },
        'thesis':   config.get('thesis', {}),
        'currency': currency,
    }
