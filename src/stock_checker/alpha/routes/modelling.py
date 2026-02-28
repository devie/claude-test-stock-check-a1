"""Modelling API routes: DCF, scenario, sensitivity, projection."""

from flask import Blueprint, request, jsonify
from stock_checker.alpha.services.modelling import (
    run_dcf, run_scenario, run_sensitivity, run_projection,
    run_pbv, run_ddm, run_roe_model,
)

bp = Blueprint("alpha_modelling", __name__)


@bp.route("/api/model/dcf", methods=["POST"])
def dcf():
    data = request.get_json()
    ticker = data.get("ticker", "").strip().upper()
    if not ticker:
        return jsonify({"error": "Ticker is required"}), 400

    try:
        result = run_dcf(
            ticker,
            growth_rate=data.get("growth_rate", 0.10),
            terminal_growth=data.get("terminal_growth", 0.03),
            wacc=data.get("wacc", 0.10),
            projection_years=data.get("projection_years", 5),
            fcf_override=data.get("fcf_override"),
        )
        return jsonify(result)
    except Exception:
        return jsonify({"error": "Failed to run DCF model"}), 500


@bp.route("/api/model/scenario", methods=["POST"])
def scenario():
    data = request.get_json()
    ticker = data.get("ticker", "").strip().upper()
    if not ticker:
        return jsonify({"error": "Ticker is required"}), 400

    try:
        result = run_scenario(
            ticker,
            scenarios=data.get("scenarios"),
            terminal_growth=data.get("terminal_growth", 0.03),
            wacc=data.get("wacc", 0.10),
            projection_years=data.get("projection_years", 5),
        )
        return jsonify(result)
    except Exception:
        return jsonify({"error": "Failed to run scenario analysis"}), 500


@bp.route("/api/model/sensitivity", methods=["POST"])
def sensitivity():
    data = request.get_json()
    ticker = data.get("ticker", "").strip().upper()
    if not ticker:
        return jsonify({"error": "Ticker is required"}), 400

    try:
        result = run_sensitivity(
            ticker,
            wacc_range=data.get("wacc_range"),
            growth_range=data.get("growth_range"),
            terminal_growth=data.get("terminal_growth", 0.03),
            projection_years=data.get("projection_years", 5),
        )
        return jsonify(result)
    except Exception:
        return jsonify({"error": "Failed to run sensitivity analysis"}), 500


@bp.route("/api/model/projection", methods=["POST"])
def projection():
    data = request.get_json()
    ticker = data.get("ticker", "").strip().upper()
    if not ticker:
        return jsonify({"error": "Ticker is required"}), 400

    try:
        result = run_projection(
            ticker,
            metric=data.get("metric", "Total Revenue"),
            periods_ahead=data.get("periods_ahead", 4),
        )
        return jsonify(result)
    except Exception:
        return jsonify({"error": "Failed to run projection"}), 500


@bp.route("/api/model/pbv", methods=["POST"])
def pbv():
    data = request.get_json()
    ticker = data.get("ticker", "").strip().upper()
    if not ticker:
        return jsonify({"error": "Ticker is required"}), 400

    try:
        result = run_pbv(
            ticker,
            cost_of_equity=data.get("cost_of_equity", 0.10),
            terminal_growth=data.get("terminal_growth", 0.05),
        )
        return jsonify(result)
    except Exception:
        return jsonify({"error": "Failed to run PBV model"}), 500


@bp.route("/api/model/ddm", methods=["POST"])
def ddm():
    data = request.get_json()
    ticker = data.get("ticker", "").strip().upper()
    if not ticker:
        return jsonify({"error": "Ticker is required"}), 400

    try:
        result = run_ddm(
            ticker,
            growth_rate=data.get("growth_rate", 0.05),
            cost_of_equity=data.get("cost_of_equity", 0.10),
        )
        return jsonify(result)
    except Exception:
        return jsonify({"error": "Failed to run DDM model"}), 500


@bp.route("/api/model/roe", methods=["POST"])
def roe_model():
    data = request.get_json()
    ticker = data.get("ticker", "").strip().upper()
    if not ticker:
        return jsonify({"error": "Ticker is required"}), 400

    try:
        result = run_roe_model(
            ticker,
            cost_of_equity=data.get("cost_of_equity", 0.10),
        )
        return jsonify(result)
    except Exception:
        return jsonify({"error": "Failed to run ROE model"}), 500
