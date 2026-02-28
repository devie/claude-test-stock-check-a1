"""Industry context route."""

from flask import Blueprint, request, jsonify
from stock_checker.alpha.services.industry import get_industry_context

bp = Blueprint('alpha_industry', __name__)


@bp.route('/api/industry', methods=['POST'])
def industry():
    data   = request.get_json() or {}
    ticker = (data.get('ticker') or '').strip().upper()
    if not ticker:
        return jsonify({'error': 'ticker required'}), 400
    try:
        result = get_industry_context(ticker)
        return jsonify(result)
    except Exception:
        return jsonify({'error': 'Failed to fetch industry data'}), 500
