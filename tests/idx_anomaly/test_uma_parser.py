"""Tests for the IDX UMA HTML parser."""
from __future__ import annotations

import pytest

from stock_checker.idx_anomaly.providers.uma_idx import (
    _normalize_ticker,
    parse_uma_html,
)


def test_parse_fixture_table(uma_html):
    entries = parse_uma_html(uma_html)
    assert len(entries) >= 3
    tickers = [e.ticker for e in entries]
    assert "BREN.JK" in tickers
    assert "GOTO.JK" in tickers
    assert "MSIN.JK" in tickers


def test_date_parsed_correctly(uma_html):
    entries = parse_uma_html(uma_html)
    bren = next(e for e in entries if e.ticker == "BREN.JK")
    assert bren.date_listed == "2025-02-03"


def test_reason_populated(uma_html):
    entries = parse_uma_html(uma_html)
    bren = next(e for e in entries if e.ticker == "BREN.JK")
    assert len(bren.reason) > 5


def test_normalize_ticker_adds_jk():
    assert _normalize_ticker("TLKM") == "TLKM.JK"


def test_normalize_ticker_keeps_existing_suffix():
    assert _normalize_ticker("BBCA.JK") == "BBCA.JK"


def test_empty_html_returns_empty_list():
    result = parse_uma_html("<html><body><p>No data</p></body></html>")
    assert result == []


def test_malformed_html_does_not_raise():
    html = "<table><tr><td>ZZZZ</td><td>Some Company</td></tr></table>"
    result = parse_uma_html(html)
    # May or may not find an entry, but must not raise
    assert isinstance(result, list)
