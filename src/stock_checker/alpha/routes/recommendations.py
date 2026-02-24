"""Daily Recommendations API routes."""

from flask import Blueprint, request, jsonify
from stock_checker.alpha.services.scores import get_scores
from stock_checker.alpha.services.ai_analysis import analyze_watchlist

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


@bp.route("/api/recommendations/ai-analyze", methods=["POST"])
def ai_analyze():
    """Run AI analysis (Claude) on a batch scores list.

    Body: { "scores": [ ...batch scores from /api/scores/batch... ] }
    Returns: list of revised score dicts with narrative field added.
    """
    data = request.get_json() or {}
    scores = data.get("scores") or []
    if not scores:
        return jsonify({"error": "scores list required"}), 400

    try:
        results = analyze_watchlist(scores)
        return jsonify(results)
    except EnvironmentError as e:
        return jsonify({"error": str(e), "code": "no_api_key"}), 503
    except Exception as e:
        return jsonify({"error": str(e)}), 500
