"""Metric computation for anomaly detection."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

import pandas as pd

MIN_ROWS = 10       # minimum rows to compute anything
MIN_SIGMA_ROWS = 20  # minimum rows for rolling std / volume median


@dataclass
class TickerMetrics:
    ticker: str
    price: float

    ret_1d: Optional[float] = None
    sigma_60d: Optional[float] = None
    z_score: Optional[float] = None

    vol_today: Optional[float] = None
    vol_median_20d: Optional[float] = None
    vol_spike_ratio: Optional[float] = None

    bvps: Optional[float] = None
    pbv_today: Optional[float] = None
    pbv_median_60d: Optional[float] = None
    pbv_jump: Optional[float] = None

    has_short_history: bool = False
    skipped_rules: list[str] = field(default_factory=list)


def compute_metrics(
    df: pd.DataFrame,
    ticker: str,
    bvps: Optional[float] = None,
) -> TickerMetrics:
    """Compute all anomaly metrics from an OHLCV DataFrame."""
    df = df[["open", "high", "low", "close", "volume"]].copy()
    df = df.dropna(subset=["close", "volume"])
    n = len(df)

    price = float(df["close"].iloc[-1]) if n > 0 else 0.0
    m = TickerMetrics(ticker=ticker, price=price)

    if n < MIN_ROWS:
        m.has_short_history = True
        m.skipped_rules = ["price_spike", "volume_spike", "pbv_jump"]
        return m

    # 1-day return
    if n >= 2:
        prev = float(df["close"].iloc[-2])
        m.ret_1d = (price - prev) / prev if prev != 0 else 0.0

    # Rolling 60-day sigma + z-score
    returns = df["close"].pct_change().dropna()
    if len(returns) >= MIN_SIGMA_ROWS:
        roll = returns.rolling(60, min_periods=MIN_SIGMA_ROWS)
        sigma = roll.std().iloc[-1]
        mean = roll.mean().iloc[-1]
        if sigma and sigma > 0:
            m.sigma_60d = float(sigma)
            if m.ret_1d is not None:
                m.z_score = (m.ret_1d - float(mean)) / float(sigma)
    else:
        m.skipped_rules.append("price_spike")

    # Volume spike ratio vs 20-day median
    m.vol_today = float(df["volume"].iloc[-1])
    vol_hist = df["volume"].iloc[:-1]
    if len(vol_hist) >= MIN_SIGMA_ROWS:
        median = vol_hist.rolling(20, min_periods=10).median().iloc[-1]
        if median and median > 0:
            m.vol_median_20d = float(median)
            m.vol_spike_ratio = m.vol_today / m.vol_median_20d
    else:
        m.skipped_rules.append("volume_spike")

    # PBV metrics (requires BVPS from fundamentals)
    if bvps and bvps > 0:
        m.bvps = float(bvps)
        m.pbv_today = price / bvps
        if n >= 60:
            pbv_series = df["close"] / bvps
            median_pbv = pbv_series.rolling(60, min_periods=20).median().iloc[-1]
            if median_pbv and median_pbv > 0:
                m.pbv_median_60d = float(median_pbv)
                m.pbv_jump = m.pbv_today / m.pbv_median_60d
        else:
            m.skipped_rules.append("pbv_jump")
    else:
        m.skipped_rules.append("pbv_jump")

    return m
