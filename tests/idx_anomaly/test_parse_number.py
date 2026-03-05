"""Tests for parse_number utility."""
from __future__ import annotations

import pytest

from stock_checker.idx_anomaly.utils.parse import parse_number


@pytest.mark.parametrize("raw,expected", [
    # Western thousand-separator
    ("1,234.56", 1234.56),
    ("1,000,000", 1_000_000.0),
    # Indonesian format: dots as thousands, comma as decimal
    ("1.234,56", 1234.56),
    ("10.500,00", 10500.0),
    # Plain integers and floats
    ("1234", 1234.0),
    ("3.14", 3.14),
    # Actual Python numbers pass through
    (1234, 1234.0),
    (3.14, 3.14),
    # None / empty
    (None, None),
    ("", None),
    # Currency prefix (IDR)
    ("Rp 5.200", 5200.0),
])
def test_parse_number(raw, expected):
    result = parse_number(raw)
    if expected is None:
        assert result is None
    else:
        assert result == pytest.approx(expected, rel=1e-6)


def test_parse_number_invalid_returns_none():
    assert parse_number("not-a-number") is None
