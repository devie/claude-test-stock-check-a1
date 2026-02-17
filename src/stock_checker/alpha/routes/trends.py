"""Trend analysis API routes."""

from flask import Blueprint, request, jsonify
from stock_checker.alpha.services.trends import get_trend_analysis

bp = Blueprint("alpha_trends", __name__)


@bp.route("/api/trends", methods=["POST"])
def trends():
    data = request.get_json()
    ticker = data.get("ticker", "").strip().upper()

    if not ticker:
        return jsonify({"error": "Ticker is required"}), 400

    try:
        result = get_trend_analysis(ticker)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
