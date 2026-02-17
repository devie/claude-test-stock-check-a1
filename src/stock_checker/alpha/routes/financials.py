"""Financial statement API routes."""

from flask import Blueprint, request, jsonify
from stock_checker.alpha.services.financials import get_financial_analysis

bp = Blueprint("alpha_financials", __name__)


@bp.route("/api/financials", methods=["POST"])
def financials():
    data = request.get_json()
    ticker = data.get("ticker", "").strip().upper()

    if not ticker:
        return jsonify({"error": "Ticker is required"}), 400

    try:
        result = get_financial_analysis(ticker)
        return jsonify(result)
    except ValueError as e:
        return jsonify({"error": str(e)}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500
