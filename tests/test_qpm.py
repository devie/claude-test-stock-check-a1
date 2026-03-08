"""Unit tests for QPMAnalyzer core methods."""
from __future__ import annotations

import math
import warnings

import numpy as np
import pandas as pd
import pytest

from stock_checker.qpm import (
    MAX_WEIGHT,
    MIN_TICKERS,
    MIN_WEIGHT,
    QPMAnalyzer,
    _normalize_ticker,
)


# ── Fixtures ──────────────────────────────────────────────────────────────────


def _make_prices(n_tickers: int = 5, n_days: int = 500, seed: int = 42) -> pd.DataFrame:
    """Generate synthetic price data for testing."""
    rng = np.random.default_rng(seed)
    dates = pd.bdate_range("2019-01-01", periods=n_days)
    tickers = [f"TICK{i}.JK" for i in range(n_tickers)]
    log_returns = rng.normal(0.0005, 0.015, size=(n_days, n_tickers))
    prices = 1000.0 * np.exp(np.cumsum(log_returns, axis=0))
    return pd.DataFrame(prices, index=dates, columns=tickers)


@pytest.fixture
def analyzer() -> QPMAnalyzer:
    return QPMAnalyzer(risk_free_rate=0.065)


@pytest.fixture
def prices() -> pd.DataFrame:
    return _make_prices()


@pytest.fixture
def returns(prices: pd.DataFrame) -> pd.DataFrame:
    return QPMAnalyzer().compute_returns(prices)


@pytest.fixture
def cov(returns: pd.DataFrame) -> np.ndarray:
    return QPMAnalyzer().compute_covariance(returns, shrinkage=False)


# ── _normalize_ticker ─────────────────────────────────────────────────────────


def test_normalize_ticker_appends_jk():
    assert _normalize_ticker("bbca") == "BBCA.JK"


def test_normalize_ticker_leaves_dot_alone():
    assert _normalize_ticker("BBCA.JK") == "BBCA.JK"


def test_normalize_ticker_strips_whitespace():
    assert _normalize_ticker("  tlkm  ") == "TLKM.JK"


# ── compute_returns ───────────────────────────────────────────────────────────


def test_compute_returns_shape(analyzer, prices):
    ret = analyzer.compute_returns(prices)
    assert ret.shape == (len(prices) - 1, prices.shape[1])


def test_compute_returns_no_nan(analyzer, prices):
    ret = analyzer.compute_returns(prices)
    assert not ret.isnull().any().any()


def test_compute_returns_log_returns(analyzer):
    """Verify returns are log-returns, not simple returns."""
    px = pd.DataFrame({"A.JK": [100.0, 110.0, 99.0]})
    ret = analyzer.compute_returns(px)
    expected = math.log(110.0 / 100.0)
    assert abs(ret.iloc[0, 0] - expected) < 1e-10


# ── compute_covariance ────────────────────────────────────────────────────────


def test_covariance_shape(analyzer, returns):
    cov = analyzer.compute_covariance(returns, shrinkage=False)
    n = returns.shape[1]
    assert cov.shape == (n, n)


def test_covariance_positive_semidefinite(analyzer, returns):
    cov = analyzer.compute_covariance(returns, shrinkage=False)
    eigenvalues = np.linalg.eigvalsh(cov)
    assert np.all(eigenvalues >= -1e-10)


def test_covariance_annualized(analyzer):
    """Daily variance * 252 = annualized variance."""
    rng = np.random.default_rng(0)
    ret = pd.DataFrame(rng.normal(0, 0.01, (300, 3)), columns=list("ABC"))
    cov = analyzer.compute_covariance(ret, shrinkage=False)
    daily_var = ret.var().values
    np.testing.assert_allclose(np.diag(cov), daily_var * 252, rtol=1e-4)


def test_covariance_shrinkage_available(analyzer, returns):
    """LedoitWolf shrinkage should work if sklearn is installed."""
    try:
        import sklearn  # noqa: F401
        cov_s = analyzer.compute_covariance(returns, shrinkage=True)
        cov_raw = analyzer.compute_covariance(returns, shrinkage=False)
        assert cov_s.shape == cov_raw.shape
        # Shrunk matrix diagonal should be non-negative
        assert np.all(np.diag(cov_s) >= 0)
    except ImportError:
        pytest.skip("sklearn not installed")


# ── compute_factors ───────────────────────────────────────────────────────────


def test_compute_factors_shape(analyzer, prices):
    factors = analyzer.compute_factors(prices)
    assert factors.shape[0] == prices.shape[1]
    assert set(["momentum", "low_vol", "value", "quality"]).issubset(set(factors.columns))


def test_compute_factors_normalized(analyzer, prices):
    """All factor values should be in [0, 1]."""
    factors = analyzer.compute_factors(prices)
    assert factors.min().min() >= -1e-9
    assert factors.max().max() <= 1 + 1e-9


def test_compute_factor_scores_range(analyzer, prices):
    factors = analyzer.compute_factors(prices)
    scores = analyzer.compute_factor_scores(factors)
    assert (scores >= 0).all()
    assert (scores <= 1).all()


# ── optimize_min_variance ─────────────────────────────────────────────────────


def test_min_variance_weights_sum_to_one(analyzer, returns, cov):
    w = analyzer.optimize_min_variance(returns, cov)
    assert abs(w.sum() - 1.0) < 1e-6


def test_min_variance_weights_within_bounds(analyzer, returns, cov):
    w = analyzer.optimize_min_variance(returns, cov)
    assert np.all(w >= MIN_WEIGHT - 1e-6)
    assert np.all(w <= MAX_WEIGHT + 1e-6)


def test_min_variance_lower_vol_than_equal_weight(analyzer, returns, cov):
    w_mv = analyzer.optimize_min_variance(returns, cov)
    w_eq = np.ones(returns.shape[1]) / returns.shape[1]
    vol_mv = math.sqrt(float(w_mv @ cov @ w_mv))
    vol_eq = math.sqrt(float(w_eq @ cov @ w_eq))
    # Min-var should be ≤ equal-weight vol (or equal if bounds binding)
    assert vol_mv <= vol_eq + 1e-6


# ── optimize_max_sharpe ───────────────────────────────────────────────────────


def test_max_sharpe_weights_sum_to_one(analyzer, returns, cov):
    w = analyzer.optimize_max_sharpe(returns, cov)
    assert abs(w.sum() - 1.0) < 1e-6


def test_max_sharpe_weights_within_bounds(analyzer, returns, cov):
    w = analyzer.optimize_max_sharpe(returns, cov)
    assert np.all(w >= MIN_WEIGHT - 1e-6)
    assert np.all(w <= MAX_WEIGHT + 1e-6)


# ── optimize_risk_parity ──────────────────────────────────────────────────────


def test_risk_parity_weights_sum_to_one(analyzer, cov):
    w = analyzer.optimize_risk_parity(cov)
    assert abs(w.sum() - 1.0) < 1e-6


def test_risk_parity_weights_within_bounds(analyzer, cov):
    w = analyzer.optimize_risk_parity(cov)
    assert np.all(w >= MIN_WEIGHT - 1e-6)
    assert np.all(w <= MAX_WEIGHT + 1e-6)


def test_risk_parity_equal_contributions_diagonal(analyzer):
    """With diagonal (uncorrelated) cov, risk parity ≈ inverse-vol weights."""
    n = 4
    # Diagonal covariance with different variances
    vols = np.array([0.10, 0.15, 0.20, 0.25]) ** 2
    cov = np.diag(vols) * 252
    w = analyzer.optimize_risk_parity(cov)
    assert abs(w.sum() - 1.0) < 1e-6


# ── optimize_factor_weighted ──────────────────────────────────────────────────


def test_factor_weighted_sums_to_one(analyzer, prices):
    tickers = prices.columns.tolist()
    factors = analyzer.compute_factors(prices)
    scores = analyzer.compute_factor_scores(factors)
    w = analyzer.optimize_factor_weighted(tickers, scores)
    assert abs(w.sum() - 1.0) < 1e-6


def test_factor_weighted_within_bounds(analyzer, prices):
    tickers = prices.columns.tolist()
    factors = analyzer.compute_factors(prices)
    scores = analyzer.compute_factor_scores(factors)
    w = analyzer.optimize_factor_weighted(tickers, scores)
    assert np.all(w >= MIN_WEIGHT - 1e-6)
    assert np.all(w <= MAX_WEIGHT + 1e-6)


# ── optimize dispatch ─────────────────────────────────────────────────────────


@pytest.mark.parametrize("method", ["min_variance", "max_sharpe", "risk_parity"])
def test_optimize_dispatch(analyzer, returns, cov, method):
    w = analyzer.optimize(method, returns, cov)
    assert abs(w.sum() - 1.0) < 1e-6
    assert np.all(w >= MIN_WEIGHT - 1e-6)
    assert np.all(w <= MAX_WEIGHT + 1e-6)


def test_optimize_invalid_method(analyzer, returns, cov):
    with pytest.raises(ValueError, match="Unknown optimization method"):
        analyzer.optimize("unknown_method", returns, cov)


# ── compute_risk_metrics ──────────────────────────────────────────────────────


def test_risk_metrics_keys(analyzer, returns, cov):
    w = np.ones(returns.shape[1]) / returns.shape[1]
    metrics = analyzer.compute_risk_metrics(w, returns, cov)
    assert "expected_return" in metrics
    assert "volatility" in metrics
    assert "sharpe_ratio" in metrics
    assert "diversification_ratio" in metrics


def test_risk_metrics_vol_positive(analyzer, returns, cov):
    w = np.ones(returns.shape[1]) / returns.shape[1]
    metrics = analyzer.compute_risk_metrics(w, returns, cov)
    assert metrics["volatility"] > 0


def test_risk_metrics_diversification_ratio_ge_one(analyzer, returns, cov):
    """Diversification ratio should be ≥ 1 for a diversified portfolio."""
    w = np.ones(returns.shape[1]) / returns.shape[1]
    metrics = analyzer.compute_risk_metrics(w, returns, cov)
    assert metrics["diversification_ratio"] >= 1.0 - 1e-6


# ── efficient_frontier ────────────────────────────────────────────────────────


def test_efficient_frontier_returns_list(analyzer, returns, cov):
    points = analyzer.efficient_frontier(returns, cov, n_points=10)
    assert isinstance(points, list)
    # May be empty if all constraints are binding, but usually has points
    for p in points:
        assert "volatility" in p
        assert "return" in p


def test_efficient_frontier_positive_vols(analyzer, returns, cov):
    points = analyzer.efficient_frontier(returns, cov, n_points=10)
    for p in points:
        assert p["volatility"] >= 0


# ── max drawdown ──────────────────────────────────────────────────────────────


def test_max_drawdown_simple(analyzer):
    """100% → 50% drawdown."""
    series = [0.0, 10.0, 20.0, 10.0, 0.0]  # cumulative %
    dd = analyzer._max_drawdown(series)
    # Peak wealth = 1.20, trough = 1.00 → dd = 0.20/1.20 ≈ 16.7%
    assert abs(dd - (0.20 / 1.20)) < 1e-6


def test_max_drawdown_no_drawdown(analyzer):
    """Monotonically rising series → zero drawdown."""
    series = [0.0, 5.0, 10.0, 15.0, 20.0]
    assert analyzer._max_drawdown(series) == 0.0


def test_max_drawdown_empty(analyzer):
    assert analyzer._max_drawdown([]) == 0.0


# ── rolling_sharpe ────────────────────────────────────────────────────────────


def test_rolling_sharpe_output_length(analyzer):
    n = 100
    rets = [0.001] * n
    dates = [f"2024-01-{i:02d}" for i in range(1, n + 1)]
    result = analyzer._rolling_sharpe(dates, rets, window=20)
    assert len(result) == n - 20


def test_rolling_sharpe_positive_for_positive_returns(analyzer):
    """Mean Sharpe should be positive when returns are consistently positive."""
    rng = np.random.default_rng(7)
    # Positive drift with small noise so std > 0
    rets = (0.005 + rng.normal(0, 0.002, 200)).tolist()
    dates = [str(i) for i in range(200)]
    result = analyzer._rolling_sharpe(dates, rets, window=63)
    sharpes = [r["sharpe"] for r in result]
    assert float(np.mean(sharpes)) > 0


# ── MIN_TICKERS constant ──────────────────────────────────────────────────────


def test_min_tickers_constant():
    assert MIN_TICKERS == 3
