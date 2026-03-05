"""Shared fixtures for idx_anomaly tests."""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

_FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def ohlcv_df() -> pd.DataFrame:
    """23-row OHLCV DataFrame loaded from fixture (last row = spike)."""
    data = json.loads((_FIXTURES / "ohlc_response.json").read_text())
    rows = data["data"]
    df = pd.DataFrame(rows)
    df["date"] = pd.to_datetime(df["date"])
    df = df.set_index("date").sort_index()
    return df.apply(pd.to_numeric, errors="coerce")


@pytest.fixture
def short_ohlcv_df() -> pd.DataFrame:
    """5-row DataFrame (too short for most rules)."""
    dates = pd.date_range("2025-01-02", periods=5, freq="B")
    return pd.DataFrame(
        {"open": 100, "high": 105, "low": 95, "close": 102, "volume": 1_000_000},
        index=dates,
    )


@pytest.fixture
def uma_html() -> str:
    return (_FIXTURES / "uma_page.html").read_text()


@pytest.fixture
def default_rules():
    from stock_checker.idx_anomaly.config import RulesConfig
    return RulesConfig()


@pytest.fixture
def default_scoring():
    from stock_checker.idx_anomaly.config import ScoringConfig
    return ScoringConfig()
