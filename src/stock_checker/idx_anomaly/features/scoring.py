"""Composite anomaly score (0–100)."""
from __future__ import annotations

from dataclasses import dataclass

from .indicators import TickerMetrics
from .rules import RuleResult
from ..config import ScoringConfig

# Saturation values: component reaches 1.0 at these levels
_Z_SAT = 5.0
_VOL_SAT = 10.0
_PBV_SAT = 5.0


@dataclass
class ScoreResult:
    score: float          # 0–100
    severity: str         # "none" | "low" | "medium" | "high" | "critical"
    components: dict[str, float]
    alert: bool


def compute_score(
    metrics: TickerMetrics,
    rules: list[RuleResult],
    cfg: ScoringConfig,
) -> ScoreResult:
    w = cfg.weights
    uma_triggered = any(r.name == "UMAFlag" and r.triggered for r in rules)

    price_z_norm = _clamp(abs(metrics.z_score or 0.0) / _Z_SAT)
    vol_norm = _clamp((metrics.vol_spike_ratio or 0.0) / _VOL_SAT)
    pbv_norm = _clamp(((metrics.pbv_jump or 1.0) - 1.0) / (_PBV_SAT - 1.0))
    uma_norm = 1.0 if uma_triggered else 0.0

    score = (
        w.price * price_z_norm
        + w.volume * vol_norm
        + w.pbv * pbv_norm
        + w.uma * uma_norm
    )
    score = min(100.0, score)

    if uma_triggered:
        score = max(score, float(cfg.alert_threshold))

    components = {
        "price_z_norm": round(price_z_norm, 4),
        "vol_norm": round(vol_norm, 4),
        "pbv_norm": round(pbv_norm, 4),
        "uma_norm": uma_norm,
        "score": round(score, 2),
    }
    alert = score >= cfg.alert_threshold or uma_triggered
    return ScoreResult(
        score=round(score, 2),
        severity=_severity(score, uma_triggered),
        components=components,
        alert=alert,
    )


def _clamp(v: float) -> float:
    return max(0.0, min(1.0, v))


def _severity(score: float, uma: bool) -> str:
    if uma:
        return "critical"
    if score >= 85:
        return "high"
    if score >= 70:
        return "medium"
    if score >= 40:
        return "low"
    return "none"
