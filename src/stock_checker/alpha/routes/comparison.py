"""Comparison API routes."""

from flask import Blueprint, request, jsonify
from stock_checker.alpha.services.comparison import compare_tickers

bp = Blueprint("alpha_comparison", __name__)


@bp.route("/api/compare", methods=["POST"])
def compare():
    data = request.get_json()
    tickers = data.get("tickers", [])
    categories = data.get("categories")

    if not tickers or len(tickers) < 2:
        return jsonify({"error": "At least 2 tickers required"}), 400
    if len(tickers) > 8:
        return jsonify({"error": "Maximum 8 tickers"}), 400

    tickers = [t.strip().upper() for t in tickers if t.strip()]

    try:
        result = compare_tickers(tickers, categories)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
