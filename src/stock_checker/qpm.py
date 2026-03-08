"""Quantitative Portfolio Management (QPM) engine.

Builds optimized portfolios from a watchlist using:
- Ledoit-Wolf shrinkage covariance estimation (sklearn)
- Min-Variance, Max-Sharpe, Risk-Parity, Factor-Weighted optimization (scipy)
- 12-1 Momentum, Low-Volatility, Value, and Quality factor signals
- Rolling monthly-rebalanced backtest vs IHSG benchmark
"""
from __future__ import annotations

import math
import warnings
from typing import Optional

import numpy as np
import pandas as pd
import yfinance as yf
from scipy.optimize import minimize as sp_minimize

RISK_FREE_RATE_DEFAULT = 0.065  # 6.5% BI Rate (IDX context)
MIN_TICKERS = 3
MAX_WEIGHT = 0.20
MIN_WEIGHT = 0.02


def _normalize_ticker(ticker: str) -> str:
    ticker = ticker.strip().upper()
    if "." not in ticker:
        ticker = f"{ticker}.JK"
    return ticker


class QPMAnalyzer:
    """Quantitative Portfolio Management analyzer."""

    def __init__(self, risk_free_rate: float = RISK_FREE_RATE_DEFAULT):
        self.rf = risk_free_rate

    # ── Data Layer ──────────────────────────────────────────────────────────

    def fetch_prices(self, tickers: list[str], period: str = "5y") -> pd.DataFrame:
        """Fetch adjusted close prices. Returns DataFrame with tickers as columns."""
        tickers = [_normalize_ticker(t) for t in tickers]
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            if len(tickers) == 1:
                raw = yf.download(
                    tickers[0], period=period, auto_adjust=True, progress=False
                )
                prices = raw[["Close"]].copy()
                prices.columns = tickers
            else:
                raw = yf.download(
                    tickers, period=period, auto_adjust=True, progress=False
                )
                if raw.empty:
                    raise ValueError("No price data returned from yfinance")
                if isinstance(raw.columns, pd.MultiIndex):
                    prices = raw["Close"].copy()
                else:
                    prices = raw.copy()

        # Drop tickers with >60% missing rows
        thresh = int(len(prices) * 0.4)
        prices = prices.dropna(thresh=max(thresh, 1), axis=1)
        prices = prices.ffill().bfill().dropna(how="all")

        if prices.empty or len(prices.columns) < 1:
            raise ValueError("No valid price data after cleaning")

        return prices

    def compute_returns(self, prices: pd.DataFrame) -> pd.DataFrame:
        """Daily log returns, dropping the first NaN row."""
        return np.log(prices / prices.shift(1)).dropna()

    def compute_covariance(
        self, returns: pd.DataFrame, shrinkage: bool = True
    ) -> np.ndarray:
        """Annualized covariance matrix with optional Ledoit-Wolf shrinkage."""
        if shrinkage:
            try:
                from sklearn.covariance import LedoitWolf

                lw = LedoitWolf()
                lw.fit(returns.values)
                return lw.covariance_ * 252
            except ImportError:
                pass
        return returns.cov().values * 252

    # ── Factor Signals ──────────────────────────────────────────────────────

    def compute_factors(self, prices: pd.DataFrame) -> pd.DataFrame:
        """
        Compute per-ticker factor signals.

        Factors:
        - momentum : 12-month return minus 1-month return (12-1 momentum)
        - low_vol  : inverse of 60-day rolling annualized std
        - value    : derived from P/E and P/BV (lower ratios → higher score)
        - quality  : ROE proxy (higher is better)

        Returns a DataFrame indexed by ticker, normalized to [0, 1].
        """
        tickers = prices.columns.tolist()
        records: dict[str, dict] = {}

        for ticker in tickers:
            px = prices[ticker].dropna()
            n = len(px)

            # Momentum: 12-1
            ret_12m = (px.iloc[-1] / px.iloc[-min(252, n)] - 1) if n >= 21 else 0.0
            ret_1m = (px.iloc[-1] / px.iloc[-min(21, n)] - 1) if n >= 5 else 0.0
            momentum = float(ret_12m - ret_1m)

            # Low Volatility: inverse of 60-day std (annualized)
            if n >= 60:
                vol_60d = px.pct_change().tail(60).std() * math.sqrt(252)
                low_vol = 1.0 / vol_60d if vol_60d > 1e-10 else 0.0
            else:
                low_vol = 0.0

            records[ticker] = {
                "momentum": momentum,
                "low_vol": float(low_vol),
                "value": 0.0,
                "quality": 0.0,
            }

        # Enrich value/quality from yfinance fundamentals
        for ticker in list(records.keys()):
            try:
                from stock_checker.alpha.services.data_fetcher import get_info

                info = get_info(ticker)
                pe = info.get("trailingPE") or info.get("forwardPE")
                pbv = info.get("priceToBook")
                roe = info.get("returnOnEquity")

                value_parts = []
                if pe and pe > 0:
                    value_parts.append(min(10.0 / pe, 1.0))
                if pbv and pbv > 0:
                    value_parts.append(min(1.0 / pbv, 1.0))
                records[ticker]["value"] = float(np.mean(value_parts)) if value_parts else 0.0

                if roe and not (isinstance(roe, float) and math.isnan(roe)):
                    records[ticker]["quality"] = float(np.clip(float(roe), 0.0, 0.5))
            except Exception:
                pass

        df = pd.DataFrame(records).T.astype(float)

        # Cross-sectional normalization to [0, 1]
        for col in df.columns:
            col_min, col_max = df[col].min(), df[col].max()
            rng = col_max - col_min
            if rng > 1e-10:
                df[col] = (df[col] - col_min) / rng
            else:
                df[col] = 0.5

        return df

    def compute_factor_scores(self, factors: pd.DataFrame) -> pd.Series:
        """Combine normalized factor signals into a composite score."""
        factor_weights = {
            "momentum": 0.30,
            "low_vol": 0.30,
            "value": 0.25,
            "quality": 0.15,
        }
        score = pd.Series(0.0, index=factors.index)
        total_w = 0.0
        for col, w in factor_weights.items():
            if col in factors.columns:
                score += factors[col] * w
                total_w += w
        if total_w > 0:
            score /= total_w
        return score

    # ── Optimization ────────────────────────────────────────────────────────

    def _bounds_and_constraints(self, n: int):
        bounds = [(MIN_WEIGHT, MAX_WEIGHT)] * n
        constraints = [{"type": "eq", "fun": lambda w: float(np.sum(w)) - 1.0}]
        return bounds, constraints

    def _minimize(self, obj_fn, n: int) -> np.ndarray:
        """Run SLSQP minimization with equal-weight fallback on failure."""
        bounds, constraints = self._bounds_and_constraints(n)
        w0 = np.ones(n) / n
        try:
            res = sp_minimize(
                obj_fn,
                w0,
                method="SLSQP",
                bounds=bounds,
                constraints=constraints,
                options={"maxiter": 1000, "ftol": 1e-9},
            )
            if res.success:
                w = np.clip(res.x, MIN_WEIGHT, MAX_WEIGHT)
                return w / w.sum()
        except Exception:
            pass
        return w0

    def optimize_min_variance(
        self, returns: pd.DataFrame, cov: np.ndarray
    ) -> np.ndarray:
        """Minimum variance portfolio."""
        def portfolio_var(w):
            return float(w @ cov @ w)

        return self._minimize(portfolio_var, len(returns.columns))

    def optimize_max_sharpe(
        self, returns: pd.DataFrame, cov: np.ndarray
    ) -> np.ndarray:
        """Maximum Sharpe Ratio portfolio (negative Sharpe minimization)."""
        ann_ret = returns.mean().values * 252

        def neg_sharpe(w):
            port_ret = float(w @ ann_ret)
            port_vol = math.sqrt(max(float(w @ cov @ w), 1e-12))
            return -(port_ret - self.rf) / port_vol

        return self._minimize(neg_sharpe, len(returns.columns))

    def optimize_risk_parity(self, cov: np.ndarray) -> np.ndarray:
        """Equal Risk Contribution (Risk Parity) portfolio."""
        n = cov.shape[0]

        def risk_parity_obj(w):
            sigma = math.sqrt(max(float(w @ cov @ w), 1e-12))
            rc = w * (cov @ w) / sigma
            target_rc = sigma / n
            return float(np.sum((rc - target_rc) ** 2))

        return self._minimize(risk_parity_obj, n)

    def optimize_factor_weighted(
        self, tickers: list[str], factor_scores: pd.Series
    ) -> np.ndarray:
        """Factor-score weighted portfolio via score-maximizing SLSQP (satisfies all bounds)."""
        n = len(tickers)
        scores = np.array([float(factor_scores.get(t, 0.0)) for t in tickers])
        total = scores.sum()
        norm_scores = scores / total if total > 1e-10 else np.ones(n) / n

        def neg_factor(w: np.ndarray) -> float:
            return -float(w @ norm_scores)

        return self._minimize(neg_factor, n)

    def optimize(
        self,
        method: str,
        returns: pd.DataFrame,
        cov: np.ndarray,
        factor_scores: Optional[pd.Series] = None,
    ) -> np.ndarray:
        """Dispatch to the named optimization method."""
        tickers = returns.columns.tolist()
        if method == "min_variance":
            return self.optimize_min_variance(returns, cov)
        elif method == "max_sharpe":
            return self.optimize_max_sharpe(returns, cov)
        elif method == "risk_parity":
            return self.optimize_risk_parity(cov)
        elif method == "factor_weighted":
            if factor_scores is None or factor_scores.empty:
                return np.ones(len(tickers)) / len(tickers)
            return self.optimize_factor_weighted(tickers, factor_scores)
        else:
            raise ValueError(f"Unknown optimization method: {method!r}")

    # ── Risk Metrics ────────────────────────────────────────────────────────

    def compute_risk_metrics(
        self, weights: np.ndarray, returns: pd.DataFrame, cov: np.ndarray
    ) -> dict:
        """Portfolio-level annualized risk and return metrics."""
        ann_ret = returns.mean().values * 252
        port_ret = float(weights @ ann_ret)
        port_vol = math.sqrt(max(float(weights @ cov @ weights), 1e-12))
        sharpe = (port_ret - self.rf) / port_vol if port_vol > 0 else 0.0

        # Diversification ratio: weighted-avg individual vol / portfolio vol
        individual_vols = np.sqrt(np.maximum(np.diag(cov), 0.0))
        weighted_vol = float(weights @ individual_vols)
        div_ratio = weighted_vol / port_vol if port_vol > 0 else 1.0

        return {
            "expected_return": round(port_ret * 100, 2),
            "volatility": round(port_vol * 100, 2),
            "sharpe_ratio": round(sharpe, 3),
            "diversification_ratio": round(div_ratio, 3),
        }

    # ── Efficient Frontier ──────────────────────────────────────────────────

    def efficient_frontier(
        self, returns: pd.DataFrame, cov: np.ndarray, n_points: int = 40
    ) -> list[dict]:
        """Generate efficient frontier points (min-variance at each target return)."""
        ann_ret = returns.mean() * 252
        n = len(returns.columns)
        bounds = [(MIN_WEIGHT, MAX_WEIGHT)] * n
        base_constraints = [{"type": "eq", "fun": lambda w: float(np.sum(w)) - 1.0}]

        r_min = float(ann_ret.min()) * 0.8
        r_max = float(ann_ret.max()) * 0.9
        frontier: list[dict] = []

        for target in np.linspace(r_min, r_max, n_points):
            constraints = base_constraints + [
                {
                    "type": "eq",
                    "fun": lambda w, t=target: float(w @ ann_ret.values) - t,
                }
            ]
            w0 = np.ones(n) / n
            try:
                res = sp_minimize(
                    lambda w: float(w @ cov @ w),
                    w0,
                    method="SLSQP",
                    bounds=bounds,
                    constraints=constraints,
                    options={"maxiter": 500, "ftol": 1e-8},
                )
                if res.success:
                    w = np.clip(res.x, 0, 1)
                    w /= w.sum()
                    vol = math.sqrt(max(float(w @ cov @ w), 0.0))
                    frontier.append(
                        {
                            "volatility": round(vol * 100, 2),
                            "return": round(float(target) * 100, 2),
                        }
                    )
            except Exception:
                pass

        return frontier

    # ── Backtest ────────────────────────────────────────────────────────────

    def _fetch_benchmark(
        self, ticker: str, index: pd.DatetimeIndex
    ) -> pd.Series:
        """Fetch benchmark log-returns, reindexed to match portfolio dates."""
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                raw = yf.download(
                    ticker, period="6y", auto_adjust=True, progress=False
                )
            bench_px = raw["Close"].squeeze()
            bench_ret = np.log(bench_px / bench_px.shift(1)).dropna()
            return bench_ret.reindex(index).fillna(0.0)
        except Exception:
            return pd.Series(0.0, index=index)

    def backtest(
        self, prices: pd.DataFrame, method: str, benchmark: str = "^JKSE"
    ) -> dict:
        """
        Rolling backtest with monthly rebalancing.

        For each month:
          1. Recompute weights using trailing 252-day history.
          2. Apply weights to next month's daily returns.

        Returns cumulative returns (portfolio + benchmark), max drawdown,
        rebalance dates, and rolling 63-day Sharpe.
        """
        returns = self.compute_returns(prices)
        bench_ret = self._fetch_benchmark(benchmark, returns.index)

        month_ends = returns.resample("ME").last().index.tolist()
        if len(month_ends) < 2:
            return {"error": "Insufficient data for backtest (need at least 2 months)"}

        current_weights = np.ones(len(prices.columns)) / len(prices.columns)
        cum_port = 1.0
        cum_bench = 1.0
        port_daily: list[dict] = []
        bench_series: list[dict] = []
        rebalance_dates: list[str] = []

        for i in range(len(month_ends) - 1):
            rebal_date = month_ends[i]
            next_rebal = month_ends[i + 1]

            # Rebalance at month-end using trailing 252-day data
            hist = returns.loc[:rebal_date]
            if len(hist) >= 60:
                trail = hist.tail(252)
                try:
                    cov = self.compute_covariance(trail, shrinkage=True)
                    if method == "factor_weighted":
                        trail_prices = prices.loc[trail.index]
                        factors = self.compute_factors(trail_prices)
                        fs = self.compute_factor_scores(factors)
                        current_weights = self.optimize(
                            method, trail, cov, factor_scores=fs
                        )
                    else:
                        current_weights = self.optimize(method, trail, cov)
                    rebalance_dates.append(rebal_date.strftime("%Y-%m-%d"))
                except Exception:
                    pass

            # Apply weights to next month's daily returns
            mask = (returns.index > rebal_date) & (returns.index <= next_rebal)
            for dt, row in returns.loc[mask].iterrows():
                port_r = float(current_weights @ row.fillna(0.0).values)
                bench_r = float(bench_ret.get(dt, 0.0))
                cum_port *= math.exp(port_r)
                cum_bench *= math.exp(bench_r)
                date_str = dt.strftime("%Y-%m-%d")
                port_daily.append(
                    {
                        "date": date_str,
                        "cumulative": round((cum_port - 1) * 100, 4),
                        "_ret": port_r,  # internal — stripped below
                    }
                )
                bench_series.append(
                    {"date": date_str, "cumulative": round((cum_bench - 1) * 100, 4)}
                )

        if not port_daily:
            return {"error": "No backtest data produced — watchlist may be too small"}

        # Strip internal field
        port_series = [{"date": d["date"], "cumulative": d["cumulative"]} for d in port_daily]
        daily_rets = [d["_ret"] for d in port_daily]
        dates = [d["date"] for d in port_daily]

        max_dd = self._max_drawdown([x["cumulative"] for x in port_series])
        rolling_sharpe = self._rolling_sharpe(dates, daily_rets, window=63)

        return {
            "portfolio": port_series,
            "benchmark": bench_series,
            "max_drawdown": round(max_dd * 100, 2),
            "rebalance_dates": rebalance_dates,
            "rolling_sharpe": rolling_sharpe,
        }

    def _max_drawdown(self, cum_pct_series: list[float]) -> float:
        """Maximum drawdown from a cumulative % return series."""
        if not cum_pct_series:
            return 0.0
        wealth = [1.0 + v / 100 for v in cum_pct_series]
        peak = wealth[0]
        max_dd = 0.0
        for w in wealth:
            peak = max(peak, w)
            dd = (peak - w) / peak if peak > 0 else 0.0
            max_dd = max(max_dd, dd)
        return max_dd

    def _rolling_sharpe(
        self, dates: list[str], daily_rets: list[float], window: int = 63
    ) -> list[dict]:
        """Rolling annualized Sharpe Ratio over a given window."""
        result = []
        for i in range(window, len(daily_rets)):
            chunk = daily_rets[i - window: i]
            avg = float(np.mean(chunk)) * 252
            std = float(np.std(chunk)) * math.sqrt(252)
            sharpe = (avg - self.rf) / std if std > 1e-10 else 0.0
            result.append({"date": dates[i], "sharpe": round(sharpe, 3)})
        return result
