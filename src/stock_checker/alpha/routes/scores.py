"""Scores API route: POST /api/scores."""

from flask import Blueprint, request, jsonify
from stock_checker.alpha.services.scores import get_scores

bp = Blueprint("alpha_scores", __name__)


@bp.route("/api/scores", methods=["POST"])
def scores():
    data = request.get_json()
    ticker = (data.get("ticker") or "").strip().upper()
    if not ticker:
        return jsonify({"error": "Ticker is required"}), 400

    try:
        result = get_scores(ticker)
        return jsonify(result)
    except Exception:
        return jsonify({"error": "Failed to compute scores"}), 500
