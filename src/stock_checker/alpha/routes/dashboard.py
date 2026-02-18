"""Dashboard route - serves the SPA shell and price history API."""

import math
from flask import Blueprint, render_template, request, jsonify
from stock_checker.alpha.services.data_fetcher import get_history

bp = Blueprint("alpha_dashboard", __name__)


@bp.route("/")
def index():
    """Serve the Alpha SPA shell."""
    return render_template("alpha/index.html")


@bp.route("/api/price-history", methods=["POST"])
def price_history():
    """Get OHLCV price history with optional technical indicators.

    Body: {ticker, period, indicators: ["SMA20","SMA50","EMA12","EMA26","RSI14","MACD","BB20"]}
    """
    data = request.get_json()
    ticker = data.get("ticker", "").strip().upper()
    if not ticker:
        return jsonify({"error": "Ticker is required"}), 400

    period = data.get("period", "1y")
    indicators = data.get("indicators", [])

    try:
        hist = get_history(ticker, period)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    # Build OHLCV arrays
    dates = [d.strftime("%Y-%m-%d") for d in hist.index]
    opens = [_safe_float(v) for v in hist["Open"]]
    highs = [_safe_float(v) for v in hist["High"]]
    lows = [_safe_float(v) for v in hist["Low"]]
    closes = [_safe_float(v) for v in hist["Close"]]
    volumes = [_safe_float(v) for v in hist["Volume"]]

    result = {
        "ticker": ticker,
        "period": period,
        "dates": dates,
        "open": opens,
        "high": highs,
        "low": lows,
        "close": closes,
        "volume": volumes,
        "indicators": {},
    }

    close_series = hist["Close"].values

    # Calculate requested indicators
    for ind in indicators:
        ind_upper = ind.upper()
        if ind_upper.startswith("SMA"):
            window = int(ind_upper[3:]) if len(ind_upper) > 3 else 20
            result["indicators"][ind] = _calc_sma(close_series, window)
        elif ind_upper.startswith("EMA"):
            window = int(ind_upper[3:]) if len(ind_upper) > 3 else 12
            result["indicators"][ind] = _calc_ema(close_series, window)
        elif ind_upper.startswith("RSI"):
            window = int(ind_upper[3:]) if len(ind_upper) > 3 else 14
            result["indicators"][ind] = _calc_rsi(close_series, window)
        elif ind_upper == "MACD":
            macd, signal, histogram = _calc_macd(close_series)
            result["indicators"]["MACD"] = macd
            result["indicators"]["MACD_Signal"] = signal
            result["indicators"]["MACD_Hist"] = histogram
        elif ind_upper.startswith("BB"):
            window = int(ind_upper[2:]) if len(ind_upper) > 2 else 20
            upper, middle, lower = _calc_bollinger(close_series, window)
            result["indicators"]["BB_Upper"] = upper
            result["indicators"]["BB_Middle"] = middle
            result["indicators"]["BB_Lower"] = lower

    return jsonify(result)


def _safe_float(v):
    if v is None:
        return None
    f = float(v)
    if math.isnan(f) or math.isinf(f):
        return None
    return round(f, 4)


def _calc_sma(data, window):
    """Simple Moving Average."""
    result = [None] * len(data)
    for i in range(window - 1, len(data)):
        result[i] = round(float(sum(data[i - window + 1:i + 1]) / window), 4)
    return result


def _calc_ema(data, window):
    """Exponential Moving Average."""
    result = [None] * len(data)
    multiplier = 2 / (window + 1)
    # Start with SMA for first value
    if len(data) >= window:
        sma = float(sum(data[:window]) / window)
        result[window - 1] = round(sma, 4)
        for i in range(window, len(data)):
            ema = (float(data[i]) - result[i - 1]) * multiplier + result[i - 1]
            result[i] = round(ema, 4)
    return result


def _calc_rsi(data, window=14):
    """Relative Strength Index."""
    result = [None] * len(data)
    if len(data) < window + 1:
        return result

    gains = []
    losses = []
    for i in range(1, len(data)):
        change = float(data[i] - data[i - 1])
        gains.append(max(change, 0))
        losses.append(max(-change, 0))

    # First average
    avg_gain = sum(gains[:window]) / window
    avg_loss = sum(losses[:window]) / window

    if avg_loss == 0:
        result[window] = 100.0
    else:
        rs = avg_gain / avg_loss
        result[window] = round(100 - 100 / (1 + rs), 2)

    for i in range(window, len(gains)):
        avg_gain = (avg_gain * (window - 1) + gains[i]) / window
        avg_loss = (avg_loss * (window - 1) + losses[i]) / window
        if avg_loss == 0:
            result[i + 1] = 100.0
        else:
            rs = avg_gain / avg_loss
            result[i + 1] = round(100 - 100 / (1 + rs), 2)

    return result


def _calc_macd(data, fast=12, slow=26, signal_period=9):
    """MACD: EMA(12) - EMA(26), Signal: EMA(9) of MACD."""
    ema_fast = _calc_ema(data, fast)
    ema_slow = _calc_ema(data, slow)

    macd_line = [None] * len(data)
    for i in range(len(data)):
        if ema_fast[i] is not None and ema_slow[i] is not None:
            macd_line[i] = round(ema_fast[i] - ema_slow[i], 4)

    # Signal line: EMA of MACD values
    macd_vals = [v if v is not None else 0 for v in macd_line]
    signal_line = _calc_ema(macd_vals, signal_period)
    # Null out signal where MACD is null
    for i in range(len(signal_line)):
        if macd_line[i] is None:
            signal_line[i] = None

    histogram = [None] * len(data)
    for i in range(len(data)):
        if macd_line[i] is not None and signal_line[i] is not None:
            histogram[i] = round(macd_line[i] - signal_line[i], 4)

    return macd_line, signal_line, histogram


def _calc_bollinger(data, window=20, std_dev=2):
    """Bollinger Bands: Middle (SMA), Upper (+2σ), Lower (-2σ)."""
    import numpy as np
    upper = [None] * len(data)
    middle = [None] * len(data)
    lower = [None] * len(data)

    for i in range(window - 1, len(data)):
        segment = data[i - window + 1:i + 1]
        sma = float(np.mean(segment))
        std = float(np.std(segment))
        middle[i] = round(sma, 4)
        upper[i] = round(sma + std_dev * std, 4)
        lower[i] = round(sma - std_dev * std, 4)

    return upper, middle, lower
