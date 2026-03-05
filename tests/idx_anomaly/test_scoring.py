"""Tests for features/scoring.py"""
from __future__ import annotations

import pytest

from stock_checker.idx_anomaly.config import ScoringConfig
from stock_checker.idx_anomaly.features.indicators import TickerMetrics
from stock_checker.idx_anomaly.features.rules import RuleResult, evaluate_all
from stock_checker.idx_anomaly.features.scoring import compute_score


def _no_rules():
    return [
        RuleResult("PriceSpike", False, "ok", "warning"),
        RuleResult("VolumeSpike", False, "ok", "warning"),
        RuleResult("PBVJump", False, "ok", "warning"),
        RuleResult("UMAFlag", False, "ok", "warning"),
    ]


def _uma_rules():
    return [
        RuleResult("PriceSpike", False, "ok", "warning"),
        RuleResult("VolumeSpike", False, "ok", "warning"),
        RuleResult("PBVJump", False, "ok", "warning"),
        RuleResult("UMAFlag", True, "on uma list", "critical"),
    ]


def test_zero_score_on_no_signals(default_scoring):
    m = TickerMetrics(ticker="X.JK", price=1000.0)
    result = compute_score(m, _no_rules(), default_scoring)
    assert result.score == pytest.approx(0.0)
    assert result.severity == "none"
    assert not result.alert


def test_uma_forces_score_above_threshold(default_scoring):
    m = TickerMetrics(ticker="X.JK", price=1000.0)
    result = compute_score(m, _uma_rules(), default_scoring)
    assert result.score >= default_scoring.alert_threshold
    assert result.alert
    assert result.severity == "critical"


def test_high_z_score_contributes(default_scoring):
    m = TickerMetrics(ticker="X.JK", price=1000.0, z_score=5.0)
    result = compute_score(m, _no_rules(), default_scoring)
    # z_score=5 → price_z_norm=1.0 → 40 * 1.0 = 40 points
    assert result.score == pytest.approx(40.0, abs=1.0)


def test_vol_spike_contributes(default_scoring):
    m = TickerMetrics(ticker="X.JK", price=1000.0, vol_spike_ratio=10.0)
    result = compute_score(m, _no_rules(), default_scoring)
    # vol_norm=1.0 → 30 * 1.0 = 30 points
    assert result.score == pytest.approx(30.0, abs=1.0)


def test_alert_threshold_at_70(default_scoring):
    m = TickerMetrics(ticker="X.JK", price=1000.0, z_score=5.0, vol_spike_ratio=10.0)
    result = compute_score(m, _no_rules(), default_scoring)
    # 40 + 30 = 70 → should trigger alert
    assert result.alert


def test_score_capped_at_100(default_scoring):
    m = TickerMetrics(
        ticker="X.JK", price=1000.0,
        z_score=10.0, vol_spike_ratio=20.0,
        pbv_today=50.0, pbv_jump=10.0,
    )
    result = compute_score(m, _uma_rules(), default_scoring)
    assert result.score <= 100.0


def test_severity_levels(default_scoring):
    from stock_checker.idx_anomaly.features.scoring import _severity
    assert _severity(90, False) == "high"
    assert _severity(75, False) == "medium"
    assert _severity(50, False) == "low"
    assert _severity(10, False) == "none"
    assert _severity(10, True) == "critical"
