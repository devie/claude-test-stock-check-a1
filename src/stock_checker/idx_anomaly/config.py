"""Settings — loaded from config.yml + .env."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


# ── Sub-models ────────────────────────────────────────────────────────────────

class PriceSpikeRules(BaseModel):
    min_abs_return: float = 0.08
    sigma_multiplier: float = 3.0
    vol_vs_prev_multiplier: float = 5.0


class VolumeSpikeRules(BaseModel):
    ratio_threshold: float = 6.0


class PBVJumpRules(BaseModel):
    jump_multiplier: float = 2.0
    high_pbv_threshold: float = 10.0
    high_pbv_delta_pct: float = 0.50


class RulesConfig(BaseModel):
    price_spike: PriceSpikeRules = Field(default_factory=PriceSpikeRules)
    volume_spike: VolumeSpikeRules = Field(default_factory=VolumeSpikeRules)
    pbv_jump: PBVJumpRules = Field(default_factory=PBVJumpRules)


class ScoringWeights(BaseModel):
    price: int = 40
    volume: int = 30
    pbv: int = 20
    uma: int = 10


class ScoringConfig(BaseModel):
    weights: ScoringWeights = Field(default_factory=ScoringWeights)
    alert_threshold: int = 70


class StorageConfig(BaseModel):
    backend: Literal["sqlite", "parquet"] = "sqlite"
    sqlite_path: str = "data/anomaly.db"
    parquet_dir: str = "data/parquet"


class AlertsConfig(BaseModel):
    channel: Literal["console", "slack", "teams", "email"] = "console"
    alerts_dir: str = "data/alerts"


# ── Root settings ─────────────────────────────────────────────────────────────

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # API keys (read from environment)
    ohlcdev_api_key: str = ""
    invezgo_api_key: str = ""
    finnhub_api_key: str = ""
    slack_webhook_url: str = ""
    teams_webhook_url: str = ""
    smtp_host: str = ""
    smtp_user: str = ""
    smtp_pass: str = ""
    alert_to_email: str = ""

    # Config (overridden from config.yml)
    provider_price: str = "ohlcdev"
    provider_fundamentals: str = "finnhub"
    rules: RulesConfig = Field(default_factory=RulesConfig)
    scoring: ScoringConfig = Field(default_factory=ScoringConfig)
    storage: StorageConfig = Field(default_factory=StorageConfig)
    alerts_cfg: AlertsConfig = Field(default_factory=AlertsConfig)


def load_settings(config_path: str = "config.yml") -> Settings:
    """Load settings merging config.yml overrides on top of env defaults."""
    overrides: dict[str, Any] = {}
    p = Path(config_path)
    if p.exists():
        with p.open() as f:
            yml: dict = yaml.safe_load(f) or {}
        if "providers" in yml:
            overrides["provider_price"] = yml["providers"].get("price", "ohlcdev")
            overrides["provider_fundamentals"] = yml["providers"].get("fundamentals", "finnhub")
        if "rules" in yml:
            r = yml["rules"]
            overrides["rules"] = RulesConfig(
                price_spike=PriceSpikeRules(**r.get("price_spike", {})),
                volume_spike=VolumeSpikeRules(**r.get("volume_spike", {})),
                pbv_jump=PBVJumpRules(**r.get("pbv_jump", {})),
            )
        if "scoring" in yml:
            sc = yml["scoring"]
            w = sc.get("weights", {})
            overrides["scoring"] = ScoringConfig(
                weights=ScoringWeights(**w) if w else ScoringWeights(),
                alert_threshold=sc.get("alert_threshold", 70),
            )
        if "storage" in yml:
            overrides["storage"] = StorageConfig(**yml["storage"])
        if "alerts" in yml:
            overrides["alerts_cfg"] = AlertsConfig(**yml["alerts"])
    return Settings(**overrides)
