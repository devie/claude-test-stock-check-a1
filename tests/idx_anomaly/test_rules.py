"""Tests for features/rules.py"""
from __future__ import annotations

import pytest

from stock_checker.idx_anomaly.config import RulesConfig
from stock_checker.idx_anomaly.features.indicators import TickerMetrics
from stock_checker.idx_anomaly.features.rules import evaluate_all


def _metrics(**kw) -> TickerMetrics:
    base = dict(ticker="BREN.JK", price=11400.0)
    base.update(kw)
    return TickerMetrics(**base)


def test_price_spike_triggers_on_large_return(default_rules):
    m = _metrics(ret_1d=0.10, sigma_60d=0.02, z_score=5.0)
    results = {r.name: r for r in evaluate_all(m, default_rules)}
    assert results["PriceSpike"].triggered


def test_price_spike_no_trigger_on_small_return(default_rules):
    m = _metrics(ret_1d=0.03, sigma_60d=0.02, z_score=1.5)
    results = {r.name: r for r in evaluate_all(m, default_rules)}
    assert not results["PriceSpike"].triggered


def test_volume_spike_triggers(default_rules):
    m = _metrics(vol_spike_ratio=7.0, vol_today=42_000_000, vol_median_20d=6_000_000)
    results = {r.name: r for r in evaluate_all(m, default_rules)}
    assert results["VolumeSpike"].triggered


def test_volume_spike_below_threshold(default_rules):
    m = _metrics(vol_spike_ratio=3.0)
    results = {r.name: r for r in evaluate_all(m, default_rules)}
    assert not results["VolumeSpike"].triggered


def test_pbv_jump_triggers_on_multiplier(default_rules):
    m = _metrics(pbv_today=20.0, pbv_jump=2.5, pbv_median_60d=8.0)
    results = {r.name: r for r in evaluate_all(m, default_rules)}
    assert results["PBVJump"].triggered


def test_pbv_jump_triggers_on_high_pbv_condition(default_rules):
    # pbv=11 (≥10), jump=1.6 → delta_pct=0.6 ≥ 0.5 → triggers
    m = _metrics(pbv_today=11.0, pbv_jump=1.6, pbv_median_60d=7.0)
    results = {r.name: r for r in evaluate_all(m, default_rules)}
    assert results["PBVJump"].triggered


def test_pbv_jump_skipped_with_no_fundamentals(default_rules):
    m = _metrics(skipped_rules=["pbv_jump"])
    results = {r.name: r for r in evaluate_all(m, default_rules)}
    assert not results["PBVJump"].triggered
    assert "skipped" in results["PBVJump"].reason


def test_uma_flag_triggers(default_rules):
    m = _metrics()
    results = {r.name: r for r in evaluate_all(m, default_rules, is_uma=True)}
    assert results["UMAFlag"].triggered
    assert results["UMAFlag"].severity == "critical"


def test_uma_flag_no_trigger(default_rules):
    m = _metrics()
    results = {r.name: r for r in evaluate_all(m, default_rules, is_uma=False)}
    assert not results["UMAFlag"].triggered


def test_short_history_skips_all(default_rules):
    m = _metrics(has_short_history=True, skipped_rules=["price_spike", "volume_spike", "pbv_jump"])
    results = {r.name: r for r in evaluate_all(m, default_rules)}
    assert not results["PriceSpike"].triggered
    assert not results["VolumeSpike"].triggered
    assert not results["PBVJump"].triggered
