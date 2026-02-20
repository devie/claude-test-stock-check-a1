"""Company information route."""

from flask import Blueprint, request, jsonify
from stock_checker.alpha.services.company import get_company_info

bp = Blueprint('alpha_company', __name__)


@bp.route('/api/company-info', methods=['POST'])
def company_info():
    """Get detailed company information for a ticker.

    Body: { "ticker": "BBCA.JK" }
    Returns: overview, officers, shareholders, calendar, subsidiaries note
    """
    data = request.get_json() or {}
    ticker = (data.get('ticker') or '').strip().upper()
    if not ticker:
        return jsonify({'error': 'ticker required'}), 400
    try:
        result = get_company_info(ticker)
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500
