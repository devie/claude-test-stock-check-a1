"""News aggregation route."""

from flask import Blueprint, request, jsonify
from stock_checker.alpha.services.news import get_news

bp = Blueprint('alpha_news', __name__)


@bp.route('/api/news', methods=['POST'])
def news():
    """Fetch aggregated news for a list of tickers.

    Body: { "tickers": ["BBCA.JK", "TLKM.JK", ...] }
    Returns: list of articles (max 15) sorted by date desc
    """
    data = request.get_json() or {}
    tickers = data.get('tickers') or []
    if not tickers or not isinstance(tickers, list):
        return jsonify({'error': 'tickers (list) required'}), 400
    try:
        result = get_news(tickers)
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500
