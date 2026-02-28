"""Daily Recommendations API routes."""

from flask import Blueprint, request, jsonify
from stock_checker.alpha.services.scores import get_scores
from stock_checker.alpha.services.ai_analysis import analyze_watchlist, get_provider_status

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

    tickers = tickers[:20]  # cap batch size
    results = []
    for ticker in tickers:
        ticker = ticker.strip().upper()
        if not ticker:
            continue
        try:
            result = get_scores(ticker)
            results.append(result)
        except Exception:
            results.append({"ticker": ticker, "error": "Failed to compute scores"})

    return jsonify(results)


@bp.route("/api/recommendations/ai-analyze", methods=["POST"])
def ai_analyze():
    """Run AI analysis (Claude) on a batch scores list.

    Body: { "scores": [ ...batch scores from /api/scores/batch... ] }
    Returns: list of revised score dicts with narrative field added.
    """
    data = request.get_json() or {}
    scores = data.get("scores") or []
    lang = data.get("lang", "id")
    if lang not in ("id", "en"):
        lang = "id"
    if not scores:
        return jsonify({"error": "scores list required"}), 400

    try:
        results = analyze_watchlist(scores, lang=lang)
        return jsonify(results)
    except EnvironmentError:
        status = get_provider_status()
        return jsonify({
            "error": "AI provider not configured",
            "code":  "no_api_key",
            "provider": status["provider"],
            "hint":  status["hint"],
        }), 503
    except Exception:
        return jsonify({"error": "Failed to run AI analysis"}), 500


@bp.route("/api/recommendations/ai-status", methods=["GET"])
def ai_status():
    """Return current AI provider config and readiness."""
    return jsonify(get_provider_status())
