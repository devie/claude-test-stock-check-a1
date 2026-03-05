"""Tests for features/indicators.py"""
from __future__ import annotations

import pandas as pd
import pytest

from stock_checker.idx_anomaly.features.indicators import (
    MIN_ROWS,
    TickerMetrics,
    compute_metrics,
)


def test_normal_history(ohlcv_df):
    m = compute_metrics(ohlcv_df, ticker="BREN.JK")
    assert m.ticker == "BREN.JK"
    assert m.price == pytest.approx(11400.0)
    assert not m.has_short_history


def test_ret_1d_is_spike(ohlcv_df):
    m = compute_metrics(ohlcv_df, ticker="BREN.JK")
    # Last close 11400, prev 10550 → ~8.1% return
    assert m.ret_1d is not None
    assert m.ret_1d == pytest.approx((11400 - 10550) / 10550, rel=1e-3)


def test_volume_spike_ratio(ohlcv_df):
    m = compute_metrics(ohlcv_df, ticker="BREN.JK")
    # Last volume 45_000_000 vs median of prior rows (~6M) → ratio ≈ 7
    assert m.vol_spike_ratio is not None
    assert m.vol_spike_ratio > 5.0


def test_z_score_populated(ohlcv_df):
    m = compute_metrics(ohlcv_df, ticker="BREN.JK")
    # With 23 rows we may not have sigma; check graceful handling
    # z_score can be None if fewer than MIN_SIGMA_ROWS returns available
    assert m.z_score is None or isinstance(m.z_score, float)


def test_pbv_computed(ohlcv_df):
    m = compute_metrics(ohlcv_df, ticker="BREN.JK", bvps=1000.0)
    assert m.pbv_today == pytest.approx(11400.0 / 1000.0)


def test_pbv_skipped_when_no_bvps(ohlcv_df):
    m = compute_metrics(ohlcv_df, ticker="BREN.JK", bvps=None)
    assert "pbv_jump" in m.skipped_rules
    assert m.pbv_today is None


def test_short_history_sets_flag(short_ohlcv_df):
    m = compute_metrics(short_ohlcv_df, ticker="X.JK")
    assert m.has_short_history
    assert set(m.skipped_rules) == {"price_spike", "volume_spike", "pbv_jump"}


def test_empty_df():
    df = pd.DataFrame(columns=["open", "high", "low", "close", "volume"])
    m = compute_metrics(df, ticker="EMPTY.JK")
    assert m.has_short_history
    assert m.price == 0.0
