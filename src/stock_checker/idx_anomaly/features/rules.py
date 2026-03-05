"""Rule evaluation — each rule returns a RuleResult."""
from __future__ import annotations

from dataclasses import dataclass

from .indicators import TickerMetrics
from ..config import RulesConfig


@dataclass(frozen=True)
class RuleResult:
    name: str
    triggered: bool
    reason: str
    severity: str  # "warning" | "critical"


def evaluate_all(
    metrics: TickerMetrics,
    cfg: RulesConfig,
    is_uma: bool = False,
) -> list[RuleResult]:
    return [
        _price_spike(metrics, cfg),
        _volume_spike(metrics, cfg),
        _pbv_jump(metrics, cfg),
        _uma_flag(metrics.ticker, is_uma),
    ]


def _price_spike(m: TickerMetrics, cfg: RulesConfig) -> RuleResult:
    name = "PriceSpike"
    if "price_spike" in m.skipped_rules:
        return RuleResult(name=name, triggered=False, reason="skipped:short_history", severity="warning")

    pc = cfg.price_spike
    ret = m.ret_1d or 0.0
    abs_ret = abs(ret)
    sigma = m.sigma_60d or 0.0

    threshold_static = pc.min_abs_return                          # e.g. 8 %
    threshold_sigma = pc.sigma_multiplier * sigma if sigma > 0 else float("inf")
    effective = max(threshold_static, threshold_sigma) if threshold_sigma < float("inf") else threshold_static

    triggered = abs_ret > effective
    reason = (
        f"ret_1d={ret:.2%} threshold=max({threshold_static:.0%},{threshold_sigma:.2%})"
        if triggered
        else f"ret_1d={ret:.2%} within_normal"
    )
    return RuleResult(name=name, triggered=triggered, reason=reason, severity="warning")


def _volume_spike(m: TickerMetrics, cfg: RulesConfig) -> RuleResult:
    name = "VolumeSpike"
    if "volume_spike" in m.skipped_rules:
        return RuleResult(name=name, triggered=False, reason="skipped:short_history", severity="warning")

    ratio = m.vol_spike_ratio or 0.0
    threshold = cfg.volume_spike.ratio_threshold
    triggered = ratio >= threshold
    reason = (
        f"vol_ratio={ratio:.1f}x >= {threshold:.0f}x"
        if triggered
        else f"vol_ratio={ratio:.1f}x"
    )
    return RuleResult(name=name, triggered=triggered, reason=reason, severity="warning")


def _pbv_jump(m: TickerMetrics, cfg: RulesConfig) -> RuleResult:
    name = "PBVJump"
    if "pbv_jump" in m.skipped_rules:
        return RuleResult(name=name, triggered=False, reason="skipped:no_fundamentals", severity="warning")

    pc = cfg.pbv_jump
    pbv = m.pbv_today or 0.0
    jump = m.pbv_jump or 0.0

    cond_jump = jump >= pc.jump_multiplier
    cond_high = pbv >= pc.high_pbv_threshold and (jump - 1.0) >= pc.high_pbv_delta_pct
    triggered = cond_jump or cond_high
    reason = (
        f"pbv={pbv:.2f} jump={jump:.2f}x (cond_jump={cond_jump} cond_high={cond_high})"
        if triggered
        else f"pbv={pbv:.2f} jump={jump:.2f}x"
    )
    return RuleResult(name=name, triggered=triggered, reason=reason, severity="warning")


def _uma_flag(ticker: str, is_uma: bool) -> RuleResult:
    return RuleResult(
        name="UMAFlag",
        triggered=is_uma,
        reason=f"{ticker} is on IDX UMA list" if is_uma else "not_uma",
        severity="critical" if is_uma else "warning",
    )
