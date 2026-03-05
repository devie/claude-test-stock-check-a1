"""Flask blueprint — /anomaly/* routes."""
from __future__ import annotations

import os
import threading
from datetime import datetime, timezone

from cachetools import TTLCache
from flask import Blueprint, jsonify, render_template, request

from ..config import load_settings
from ..features.indicators import compute_metrics
from ..features.rules import evaluate_all
from ..features.scoring import compute_score
from ..providers.uma_idx import IDXUMAScraper
from ..utils.logging import get_logger

_TMPL = os.path.join(os.path.dirname(__file__), "..", "templates")

bp = Blueprint(
    "idx_anomaly",
    __name__,
    url_prefix="/anomaly",
    template_folder=_TMPL,
)

logger = get_logger(__name__)
_settings = None

# UMA cache: 1-hour TTL, shared across requests
_uma_cache: TTLCache = TTLCache(maxsize=2, ttl=3600)
_uma_lock = threading.Lock()


def _cfg():
    global _settings
    if _settings is None:
        _settings = load_settings()
    return _settings


def _make_price_prov(cfg):
    """Return configured price provider (falls back to yfinance internally)."""
    if cfg.provider_price == "invezgo":
        from ..providers.price_invezgo import InvezgoProvider
        return InvezgoProvider(cfg.invezgo_api_key)
    if cfg.provider_price == "yfinance":
        from ..providers.price_yfinance import YFinanceProvider
        return YFinanceProvider()
    from ..providers.price_ohlc import OHLCDevProvider
    return OHLCDevProvider(cfg.ohlcdev_api_key)


def _fetch_uma_cached() -> set[str]:
    """Return UMA ticker set, cached for 1 hour."""
    with _uma_lock:
        if "tickers" in _uma_cache:
            return _uma_cache["tickers"]
    try:
        entries = IDXUMAScraper().fetch()
        tickers = {e.ticker for e in entries}
    except Exception as exc:
        logger.warning("UMA fetch failed: %s", exc)
        tickers = set()
    with _uma_lock:
        _uma_cache["tickers"] = tickers
    return tickers


# ── pages ─────────────────────────────────────────────────────────────────────

@bp.route("/")
def index():
    return render_template("idx_anomaly/index.html")


# ── API ───────────────────────────────────────────────────────────────────────

@bp.route("/api/screen", methods=["POST"])
def screen():
    body = request.get_json(force=True, silent=True) or {}
    raw_tickers = body.get("tickers", [])
    if not raw_tickers or not isinstance(raw_tickers, list):
        return jsonify({"error": "tickers array required"}), 400

    tickers = [t.strip().upper() for t in raw_tickers if str(t).strip()][:50]
    # Ensure IDX .JK suffix for tickers without an exchange suffix
    tickers = [f"{t}.JK" if "." not in t else t for t in tickers if t]

    cfg = _cfg()
    from ..providers.fundamentals_finnhub import FinnhubProvider
    price_prov = _make_price_prov(cfg)
    fund_prov = FinnhubProvider(cfg.finnhub_api_key)
    uma_tickers = _fetch_uma_cached()

    results = []
    for ticker in tickers:
        try:
            ohlcv = price_prov.fetch(ticker)
            fund = fund_prov.fetch(ticker)
            metrics = compute_metrics(ohlcv.df, ticker=ticker, bvps=fund.bvps)
            is_uma = ticker in uma_tickers
            rules = evaluate_all(metrics, cfg.rules, is_uma=is_uma)
            sr = compute_score(metrics, rules, cfg.scoring)
            results.append({
                "ticker": ticker,
                "score": sr.score,
                "severity": sr.severity,
                "alert": sr.alert,
                "rules_triggered": [r.name for r in rules if r.triggered],
                "price": metrics.price,
                "change_pct": round(metrics.ret_1d * 100, 2) if metrics.ret_1d is not None else None,
                "vol_ratio": round(metrics.vol_spike_ratio, 2) if metrics.vol_spike_ratio else None,
                "z_score": round(metrics.z_score, 2) if metrics.z_score else None,
                "pbv": round(metrics.pbv_today, 2) if metrics.pbv_today else None,
                "pbv_jump": round(metrics.pbv_jump, 2) if metrics.pbv_jump else None,
                "is_uma": is_uma,
                "links": {
                    "idx": (
                        "https://www.idx.co.id/en/listed-companies/company-profiles/"
                        f"?kodeEmiten={ticker.replace('.JK','')}"
                    ),
                    "chart": f"https://finance.yahoo.com/chart/{ticker}",
                },
            })
        except Exception as exc:
            logger.error("screen error %s: %s", ticker, exc)
            results.append({"ticker": ticker, "error": str(exc)})

    results.sort(key=lambda x: x.get("score", 0), reverse=True)
    return jsonify({
        "results": results,
        "run_at": datetime.now(timezone.utc).isoformat(),
    })


@bp.route("/api/alerts")
def list_alerts():
    cfg = _cfg()
    run_date = request.args.get("date")
    min_score = float(request.args.get("min_score", cfg.scoring.alert_threshold))
    try:
        if cfg.storage.backend == "parquet":
            from ..storage.repo_parquet import ParquetRepo
            repo = ParquetRepo(cfg.storage.parquet_dir)
        else:
            from ..storage.repo_sqlite import SQLiteRepo
            repo = SQLiteRepo(cfg.storage.sqlite_path)
        alerts = repo.query_alerts(run_date=run_date, min_score=min_score)
        return jsonify({"alerts": alerts})
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


@bp.route("/api/uma")
def uma_list():
    """Return cached UMA list; forces refresh if ?refresh=1."""
    if request.args.get("refresh") == "1":
        with _uma_lock:
            _uma_cache.clear()
    try:
        entries = IDXUMAScraper().fetch()
        return jsonify({
            "uma": [
                {"ticker": e.ticker, "date": e.date_listed, "reason": e.reason}
                for e in entries
            ],
            "count": len(entries),
        })
    except Exception as exc:
        return jsonify({"error": str(exc), "uma": []}), 200  # 200 so UI handles gracefully
