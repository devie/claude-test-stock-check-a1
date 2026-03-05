"""Tests for provider parsing helpers (no network calls)."""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from stock_checker.idx_anomaly.providers.price_ohlc import _parse_rows
from stock_checker.idx_anomaly.providers.price_invezgo import _parse_candles
from stock_checker.idx_anomaly.providers.fundamentals_finnhub import _to_float

_FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def ohlc_raw():
    data = json.loads((_FIXTURES / "ohlc_response.json").read_text())
    return data["data"]


def test_ohlcdev_parse_rows_shape(ohlc_raw):
    df = _parse_rows(ohlc_raw)
    assert not df.empty
    assert set(["open", "high", "low", "close", "volume"]).issubset(df.columns)
    assert isinstance(df.index, pd.DatetimeIndex)


def test_ohlcdev_parse_rows_sorted(ohlc_raw):
    df = _parse_rows(ohlc_raw)
    assert df.index.is_monotonic_increasing


def test_ohlcdev_parse_rows_numeric(ohlc_raw):
    df = _parse_rows(ohlc_raw)
    assert pd.api.types.is_numeric_dtype(df["close"])


def test_ohlcdev_parse_empty():
    df = _parse_rows([])
    assert df.empty
    assert list(df.columns) == ["open", "high", "low", "close", "volume"]


def test_invezgo_parse_candles():
    candles = [
        {"t": "2025-01-02", "o": 100, "h": 110, "l": 95, "c": 105, "v": 1_000_000},
        {"t": "2025-01-03", "o": 105, "h": 115, "l": 100, "c": 110, "v": 1_200_000},
    ]
    # Invezgo uses different key names — test that it falls back gracefully
    candles2 = [
        {"date": "2025-01-02", "open": 100, "high": 110, "low": 95, "close": 105, "volume": 1_000_000},
        {"date": "2025-01-03", "open": 105, "high": 115, "low": 100, "close": 110, "volume": 1_200_000},
    ]
    df = _parse_candles(candles2)
    assert len(df) == 2
    assert "close" in df.columns


def test_invezgo_parse_empty():
    df = _parse_candles([])
    assert df.empty


def test_to_float_conversions():
    assert _to_float(3.14) == pytest.approx(3.14)
    assert _to_float("2.5") == pytest.approx(2.5)
    assert _to_float(None) is None
    assert _to_float("N/A") is None


def test_ohlcdev_parse_last_row_is_spike(ohlc_raw):
    df = _parse_rows(ohlc_raw)
    assert df["close"].iloc[-1] == pytest.approx(11400.0)
    assert df["volume"].iloc[-1] == pytest.approx(45_000_000.0)
