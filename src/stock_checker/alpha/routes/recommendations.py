"""Daily Recommendations API route: POST /api/scores/batch."""

from flask import Blueprint, request, jsonify
from stock_checker.alpha.services.scores import get_scores

bp = Blueprint("alpha_recommendations", __name__)


@bp.route("/api/scores/batch", methods=["POST"])
def scores_batch():
    """Compute scores for a list of tickers.

    Body: { "tickers": ["BBCA.JK", "TLKM.JK", ...] }
    Returns: list of score dicts, each identical to /api/scores response.
    Errors for individual tickers are caught; the ticker entry gets
    { "ticker": "...", "error": "..." } instead.
    """
    data = request.get_json() or {}
    tickers = data.get("tickers") or []
    if not tickers or not isinstance(tickers, list):
        return jsonify({"error": "tickers (list) required"}), 400

    results = []
    for ticker in tickers:
        ticker = ticker.strip().upper()
        if not ticker:
            continue
        try:
            result = get_scores(ticker)
            results.append(result)
        except Exception as e:
            results.append({"ticker": ticker, "error": str(e)})

    return jsonify(results)
