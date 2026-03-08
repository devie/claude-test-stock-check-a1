"""QPM Flask blueprint — /qpm/* routes."""
from __future__ import annotations

import csv
import io
import traceback
from pathlib import Path

import numpy as np
import pandas as pd
from flask import Blueprint, Response, jsonify, render_template, request

bp = Blueprint(
    "qpm",
    __name__,
    url_prefix="/qpm",
    template_folder="templates",
)

_DEFAULT_RF = 0.065  # 6.5% BI Rate


def _get_rf() -> float:
    """Read risk-free rate from config.yml qpm section, fallback to 6.5%."""
    try:
        import yaml

        cfg_path = Path("config.yml")
        if cfg_path.exists():
            cfg = yaml.safe_load(cfg_path.read_text(encoding="utf-8"))
            return float(cfg.get("qpm", {}).get("risk_free_rate", _DEFAULT_RF))
    except Exception:
        pass
    return _DEFAULT_RF


# ── Pages ─────────────────────────────────────────────────────────────────────


@bp.route("/")
def dashboard():
    return render_template("qpm_dashboard.html")


# ── API ───────────────────────────────────────────────────────────────────────


@bp.route("/optimize", methods=["POST"])
def optimize():
    """
    POST /qpm/optimize
    Body: { tickers, period, method, risk_free_rate }
    Returns optimization results: weights, metrics, factor exposures, efficient frontier.
    """
    body = request.get_json(force=True, silent=True) or {}
    tickers: list[str] = [str(t).strip() for t in body.get("tickers", []) if str(t).strip()]
    period: str = body.get("period", "3y")
    method: str = body.get("method", "max_sharpe")
    rf: float = float(body.get("risk_free_rate", _get_rf()))

    if len(tickers) < 3:
        return jsonify({"error": "QPM requires minimum 3 tickers"}), 400

    valid_methods = {"min_variance", "max_sharpe", "risk_parity", "factor_weighted"}
    if method not in valid_methods:
        return (
            jsonify({"error": f"Invalid method. Choose from: {sorted(valid_methods)}"}),
            400,
        )

    if period not in {"1y", "3y", "5y"}:
        period = "3y"

    try:
        from stock_checker.qpm import MIN_TICKERS, QPMAnalyzer

        analyzer = QPMAnalyzer(risk_free_rate=rf)
        prices = analyzer.fetch_prices(tickers, period=period)
        available = prices.columns.tolist()

        if len(available) < MIN_TICKERS:
            return (
                jsonify(
                    {
                        "error": (
                            f"Only {len(available)} tickers returned data. "
                            f"Minimum {MIN_TICKERS} required."
                        ),
                        "available": available,
                    }
                ),
                422,
            )

        returns = analyzer.compute_returns(prices)
        cov = analyzer.compute_covariance(returns, shrinkage=True)

        # Factor signals
        factors_df = analyzer.compute_factors(prices)
        factor_scores = analyzer.compute_factor_scores(factors_df)

        # Optimize
        weights_arr = analyzer.optimize(method, returns, cov, factor_scores=factor_scores)
        tickers_avail = returns.columns.tolist()

        weights = {
            t: round(float(w) * 100, 2)
            for t, w in zip(tickers_avail, weights_arr)
        }

        # Portfolio metrics
        metrics = analyzer.compute_risk_metrics(weights_arr, returns, cov)

        # Efficient frontier
        try:
            frontier = analyzer.efficient_frontier(returns, cov)
        except Exception:
            frontier = []

        # Per-ticker statistics
        ann_returns = returns.mean() * 252
        vols = pd.Series(np.sqrt(np.maximum(np.diag(cov), 0.0)), index=tickers_avail)

        ticker_stats = []
        for t, w in zip(tickers_avail, weights_arr):
            row: dict = {
                "ticker": t,
                "weight": round(float(w) * 100, 2),
                "expected_return": round(float(ann_returns[t]) * 100, 2),
                "volatility": round(float(vols[t]) * 100, 2),
                "momentum": round(
                    float(factors_df.loc[t, "momentum"]) if t in factors_df.index else 0.0, 3
                ),
                "low_vol": round(
                    float(factors_df.loc[t, "low_vol"]) if t in factors_df.index else 0.0, 3
                ),
                "value": round(
                    float(factors_df.loc[t, "value"]) if t in factors_df.index else 0.0, 3
                ),
                "quality": round(
                    float(factors_df.loc[t, "quality"]) if t in factors_df.index else 0.0, 3
                ),
                "factor_score": round(float(factor_scores.get(t, 0.0)), 3),
            }
            ticker_stats.append(row)

        ticker_stats.sort(key=lambda x: x["weight"], reverse=True)

        # Portfolio-level factor exposures (weight-averaged)
        factor_exposure: dict[str, float] = {}
        for col in ("momentum", "low_vol", "value", "quality"):
            factor_exposure[col] = round(
                sum(r[col] * r["weight"] / 100 for r in ticker_stats), 3
            )

        return jsonify(
            {
                "method": method,
                "period": period,
                "risk_free_rate": rf,
                "weights": weights,
                "metrics": metrics,
                "ticker_stats": ticker_stats,
                "factor_exposure": factor_exposure,
                "efficient_frontier": frontier,
            }
        )

    except ValueError as exc:
        return jsonify({"error": str(exc)}), 422
    except Exception as exc:
        traceback.print_exc()
        return jsonify({"error": f"Optimization failed: {exc}"}), 500


@bp.route("/backtest/<method>", methods=["GET"])
def backtest(method: str):
    """
    GET /qpm/backtest/<method>?tickers=A,B,C&period=5y&rf=0.065
    Returns backtest data: cumulative returns, max drawdown, rolling Sharpe.
    """
    tickers_raw = request.args.get("tickers", "")
    period = request.args.get("period", "5y")
    rf = float(request.args.get("rf", _get_rf()))
    tickers = [t.strip() for t in tickers_raw.split(",") if t.strip()]

    if len(tickers) < 3:
        return jsonify({"error": "Minimum 3 tickers required"}), 400

    valid_methods = {"min_variance", "max_sharpe", "risk_parity", "factor_weighted"}
    if method not in valid_methods:
        return jsonify({"error": f"Invalid method: {method}"}), 400

    try:
        from stock_checker.qpm import QPMAnalyzer

        analyzer = QPMAnalyzer(risk_free_rate=rf)
        prices = analyzer.fetch_prices(tickers, period=period)
        result = analyzer.backtest(prices, method=method)
        return jsonify(result)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 422
    except Exception as exc:
        traceback.print_exc()
        return jsonify({"error": f"Backtest failed: {exc}"}), 500


@bp.route("/export", methods=["POST"])
def export_csv():
    """
    POST /qpm/export
    Body: { ticker_stats: [...], method: str }
    Returns a CSV file download.
    """
    body = request.get_json(force=True, silent=True) or {}
    ticker_stats: list[dict] = body.get("ticker_stats", [])
    method: str = body.get("method", "portfolio")

    if not ticker_stats:
        return jsonify({"error": "No data to export"}), 400

    output = io.StringIO()
    fieldnames = [
        "ticker",
        "weight",
        "expected_return",
        "volatility",
        "momentum",
        "low_vol",
        "value",
        "quality",
        "factor_score",
    ]
    writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction="ignore")
    writer.writeheader()
    writer.writerows(ticker_stats)

    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename=qpm_{method}.csv"
        },
    )


def init_qpm(app) -> None:
    """Register QPM blueprint with the Flask app."""
    app.register_blueprint(bp)
