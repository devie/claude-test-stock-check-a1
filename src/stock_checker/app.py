"""Flask web application for stock checker."""

import math
import json
import traceback
from pathlib import Path
import numpy as np
from flask import Flask, render_template, request, jsonify

# Load .env if present (ANTHROPIC_API_KEY etc.)
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

import os
import secrets

from stock_checker.fetcher import fetch_stock
from stock_checker.indicators import calc_sma, calc_rsi, get_summary, format_number
from stock_checker.alpha import init_alpha

app = Flask(
    __name__,
    template_folder=str(Path(__file__).parent / "templates"),
)
app.secret_key = os.getenv("SECRET_KEY", secrets.token_hex(32))

# Simple API key for state-mutating endpoints
APP_API_KEY = os.getenv("APP_API_KEY", "")
app.config["APP_API_KEY"] = APP_API_KEY


def require_api_key():
    """Check API key for mutating requests. Skip if APP_API_KEY not configured."""
    if not APP_API_KEY:
        return  # no key configured, allow (dev mode)
    key = request.headers.get("X-API-Key", "")
    if not secrets.compare_digest(key, APP_API_KEY):
        from flask import abort
        abort(401)


def _clean(val):
    """Convert numpy/pandas types to JSON-safe Python types. NaN -> None."""
    if val is None:
        return None
    if isinstance(val, (np.integer,)):
        return int(val)
    if isinstance(val, (np.floating, float)):
        if math.isnan(val) or math.isinf(val):
            return None
        return float(val)
    if isinstance(val, np.ndarray):
        return [_clean(v) for v in val]
    return val


def _clean_list(series):
    """Convert a pandas Series to a JSON-safe Python list."""
    return [_clean(v) for v in series]

VALID_PERIODS = ["1mo", "3mo", "6mo", "1y", "2y", "5y", "10y", "ytd", "max"]

# Initialize Alpha module
init_alpha(app)


def _build_chart_data(df, ticker):
    """Convert DataFrame to Plotly-compatible JSON for candlestick + indicators."""
    dates = df.index.strftime("%Y-%m-%d").tolist()

    traces = []

    # Candlestick
    traces.append({
        "type": "candlestick",
        "x": dates,
        "open": _clean_list(df["Open"].round(2)),
        "high": _clean_list(df["High"].round(2)),
        "low": _clean_list(df["Low"].round(2)),
        "close": _clean_list(df["Close"].round(2)),
        "name": ticker,
        "xaxis": "x",
        "yaxis": "y",
        "increasing": {"line": {"color": "#26a69a"}},
        "decreasing": {"line": {"color": "#ef5350"}},
    })

    # SMA overlays
    sma_colors = {"SMA_20": "#2196F3", "SMA_50": "#FF9800", "SMA_200": "#F44336"}
    for col, color in sma_colors.items():
        if col in df.columns:
            vals = _clean_list(df[col])
            traces.append({
                "type": "scatter",
                "mode": "lines",
                "x": dates,
                "y": vals,
                "name": col,
                "line": {"color": color, "width": 1.2},
                "xaxis": "x",
                "yaxis": "y",
            })

    # Volume bars
    vol_colors = ["#26a69a" if (_clean(c) or 0) >= (_clean(o) or 0) else "#ef5350"
                  for c, o in zip(df["Close"], df["Open"])]
    traces.append({
        "type": "bar",
        "x": dates,
        "y": _clean_list(df["Volume"]),
        "name": "Volume",
        "marker": {"color": vol_colors},
        "xaxis": "x",
        "yaxis": "y2",
        "showlegend": False,
    })

    # RSI
    if "RSI" in df.columns:
        rsi_vals = _clean_list(df["RSI"])
        traces.append({
            "type": "scatter",
            "mode": "lines",
            "x": dates,
            "y": rsi_vals,
            "name": "RSI",
            "line": {"color": "#9C27B0", "width": 1.2},
            "xaxis": "x",
            "yaxis": "y3",
        })
        # Overbought / oversold lines
        traces.append({
            "type": "scatter",
            "mode": "lines",
            "x": [dates[0], dates[-1]],
            "y": [70, 70],
            "name": "Overbought",
            "line": {"color": "#999", "width": 0.8, "dash": "dash"},
            "xaxis": "x",
            "yaxis": "y3",
            "showlegend": False,
        })
        traces.append({
            "type": "scatter",
            "mode": "lines",
            "x": [dates[0], dates[-1]],
            "y": [30, 30],
            "name": "Oversold",
            "line": {"color": "#999", "width": 0.8, "dash": "dash"},
            "xaxis": "x",
            "yaxis": "y3",
            "showlegend": False,
        })

    layout = {
        "title": {"text": f"{ticker} Stock Chart", "font": {"size": 18}},
        "xaxis": {
            "rangeslider": {"visible": False},
            "type": "date",
            "domain": [0, 1],
        },
        "yaxis": {
            "title": "Price",
            "domain": [0.38, 1.0],
            "side": "right",
        },
        "yaxis2": {
            "title": "Volume",
            "domain": [0.18, 0.35],
            "side": "right",
        },
        "yaxis3": {
            "title": "RSI",
            "domain": [0.0, 0.15],
            "side": "right",
            "range": [0, 100],
        },
        "legend": {"orientation": "h", "y": 1.02, "x": 0.5, "xanchor": "center"},
        "margin": {"l": 50, "r": 60, "t": 60, "b": 30},
        "plot_bgcolor": "#1e1e2f",
        "paper_bgcolor": "#16161e",
        "font": {"color": "#e0e0e0"},
        "xaxis_gridcolor": "#2a2a3e",
        "yaxis_gridcolor": "#2a2a3e",
        "yaxis2_gridcolor": "#2a2a3e",
        "yaxis3_gridcolor": "#2a2a3e",
        "height": 700,
    }

    return {"data": traces, "layout": layout}


def _build_technicals(df):
    """Build technical indicator dict from DataFrame."""
    latest = df.iloc[-1]
    technicals = {}

    for w in (20, 50, 200):
        col = f"SMA_{w}"
        if col in df.columns:
            val = latest[col]
            technicals[f"SMA {w}"] = f"{val:.2f}" if not np.isnan(val) else "N/A"

    if "RSI" in df.columns:
        rsi = latest["RSI"]
        if not np.isnan(rsi):
            label = "Overbought" if rsi > 70 else "Oversold" if rsi < 30 else "Neutral"
            technicals["RSI 14"] = f"{rsi:.2f} ({label})"
        else:
            technicals["RSI 14"] = "N/A"

    if len(df) >= 20:
        recent_vol = df["Volume"].tail(20).mean()
        overall_vol = df["Volume"].mean()
        ratio = recent_vol / overall_vol if overall_vol > 0 else 0
        trend = "Above average" if ratio > 1.1 else "Below average" if ratio < 0.9 else "Average"
        technicals["Volume Trend"] = f"{trend} ({ratio:.2f}x)"

    return technicals


@app.route("/")
def index():
    from flask import redirect
    return redirect("/alpha/")


@app.route("/api/analyze", methods=["POST"])
def analyze():
    data = request.get_json()
    ticker = data.get("ticker", "").strip().upper()
    period = data.get("period", "1y")

    if not ticker:
        return jsonify({"error": "Ticker is required"}), 400
    if period not in VALID_PERIODS:
        return jsonify({"error": f"Invalid period. Choose from: {VALID_PERIODS}"}), 400

    try:
        stock, df = fetch_stock(ticker, period=period)
    except ValueError as e:
        return jsonify({"error": str(e)}), 404
    except Exception as e:
        return jsonify({"error": f"Failed to fetch data: {e}"}), 500

    try:
        summary = get_summary(stock)
        summary_formatted = {
            k: format_number(v) if isinstance(v, (int, float, np.integer, np.floating)) else (v or "N/A")
            for k, v in summary.items()
        }

        df = calc_sma(df)
        df = calc_rsi(df)

        technicals = _build_technicals(df)
        chart = _build_chart_data(df, ticker)

        return jsonify({
            "ticker": ticker,
            "period": period,
            "summary": summary_formatted,
            "technicals": technicals,
            "chart": chart,
        })
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": f"Analysis failed: {e}"}), 500


def run():
    """Entry point for the web server."""
    host = os.getenv("HOST", "127.0.0.1")
    port = int(os.getenv("PORT", "5000"))
    print(f"Starting Stock Checker Web Server on {host}:{port}...")
    app.run(host=host, port=port, debug=False, use_reloader=False)


if __name__ == "__main__":
    run()
