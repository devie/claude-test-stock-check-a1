"""Typer CLI — targets: fetch:prices, fetch:fundamentals, fetch:uma, run:screen."""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Optional

import typer

from .config import load_settings
from .features.indicators import compute_metrics
from .features.rules import evaluate_all
from .features.scoring import compute_score
from .providers.uma_idx import IDXUMAScraper
from .utils.logging import get_logger

app = typer.Typer(name="idx-anomaly", add_completion=False, no_args_is_help=True)
logger = get_logger(__name__)


# ── helpers ───────────────────────────────────────────────────────────────────

def _price_provider(cfg):
    if cfg.provider_price == "invezgo":
        from .providers.price_invezgo import InvezgoProvider
        return InvezgoProvider(cfg.invezgo_api_key)
    from .providers.price_ohlc import OHLCDevProvider
    return OHLCDevProvider(cfg.ohlcdev_api_key)


def _fund_provider(cfg):
    from .providers.fundamentals_finnhub import FinnhubProvider
    return FinnhubProvider(cfg.finnhub_api_key)


def _repo(cfg):
    if cfg.storage.backend == "parquet":
        from .storage.repo_parquet import ParquetRepo
        return ParquetRepo(cfg.storage.parquet_dir)
    from .storage.repo_sqlite import SQLiteRepo
    return SQLiteRepo(cfg.storage.sqlite_path)


def _notifier(cfg):
    ch = cfg.alerts_cfg.channel
    if ch == "teams":
        from .notifiers.teams import TeamsNotifier
        return TeamsNotifier(cfg.teams_webhook_url)
    if ch == "email":
        from .notifiers.email import EmailNotifier
        return EmailNotifier(cfg.smtp_host, cfg.smtp_user, cfg.smtp_pass, cfg.alert_to_email)
    return None  # console


def _normalize(tickers: list[str]) -> list[str]:
    """Upper-case and add .JK suffix if ticker has no exchange suffix."""
    out = []
    for t in tickers:
        t = t.strip().upper()
        if t and "." not in t:
            t = f"{t}.JK"
        if t:
            out.append(t)
    return out


# ── commands ──────────────────────────────────────────────────────────────────

@app.command("fetch:prices")
def fetch_prices(
    tickers: list[str] = typer.Argument(..., help="Ticker(s) e.g. BBCA.JK TLKM.JK"),
    days: int = typer.Option(90, help="History window (calendar days)"),
    config: str = typer.Option("config.yml"),
) -> None:
    """Fetch OHLCV prices and persist to storage."""
    cfg = load_settings(config)
    provider = _price_provider(cfg)
    repo = _repo(cfg)
    run_date = datetime.utcnow().date().isoformat()

    for ticker in _normalize(tickers):
        try:
            ohlcv = provider.fetch(ticker, days=days)
            last_close = float(ohlcv.df["close"].iloc[-1]) if len(ohlcv.df) else None
            repo.upsert(run_date, ticker, 0.0, "fetched", False,
                        {"rows": len(ohlcv.df), "last_close": last_close})
            typer.echo(f"[OK]  {ticker}: {len(ohlcv.df)} rows, last_close={last_close}")
        except Exception as exc:
            typer.echo(f"[ERR] {ticker}: {exc}", err=True)


@app.command("fetch:fundamentals")
def fetch_fundamentals(
    tickers: list[str] = typer.Argument(...),
    config: str = typer.Option("config.yml"),
) -> None:
    """Fetch BVPS / PBV from Finnhub and print."""
    cfg = load_settings(config)
    provider = _fund_provider(cfg)

    for ticker in _normalize(tickers):
        try:
            fund = provider.fetch(ticker)
            typer.echo(f"[OK]  {ticker}: bvps={fund.bvps} pbv_ttm={fund.pbv_ttm}")
        except Exception as exc:
            typer.echo(f"[ERR] {ticker}: {exc}", err=True)


@app.command("fetch:uma")
def fetch_uma(config: str = typer.Option("config.yml")) -> None:
    """Scrape IDX UMA list and print results."""
    _cfg = load_settings(config)
    scraper = IDXUMAScraper()
    entries = scraper.fetch()
    for e in entries:
        typer.echo(f"UMA  {e.ticker}  date={e.date_listed}  {e.reason[:80]}")
    typer.echo(f"\nTotal: {len(entries)} UMA entry/entries")


@app.command("run:screen")
def run_screen(
    tickers: list[str] = typer.Argument(..., help="Tickers to screen"),
    config: str = typer.Option("config.yml"),
    alert_threshold: Optional[int] = typer.Option(None, help="Override score threshold"),
    days: int = typer.Option(90, help="History window for price fetch"),
) -> None:
    """Full pipeline: fetch → compute → score → persist → alert."""
    cfg = load_settings(config)
    if alert_threshold is not None:
        cfg.scoring.alert_threshold = alert_threshold

    price_prov = _price_provider(cfg)
    fund_prov = _fund_provider(cfg)
    repo = _repo(cfg)
    notifier = _notifier(cfg)
    run_date = datetime.utcnow().date().isoformat()

    # Fetch UMA list once
    try:
        uma_entries = IDXUMAScraper().fetch()
        uma_tickers = {e.ticker for e in uma_entries}
    except Exception as exc:
        logger.warning("UMA fetch failed: %s", exc)
        uma_tickers = set()

    alerts_dir = Path(cfg.alerts_cfg.alerts_dir)
    alerts_dir.mkdir(parents=True, exist_ok=True)
    alerts_file = alerts_dir / f"alerts_{run_date}.jsonl"
    alert_records: list[dict] = []

    for ticker in _normalize(tickers):
        try:
            ohlcv = price_prov.fetch(ticker, days=days)
            fund = fund_prov.fetch(ticker)
            metrics = compute_metrics(ohlcv.df, ticker=ticker, bvps=fund.bvps)
            is_uma = ticker in uma_tickers
            rules = evaluate_all(metrics, cfg.rules, is_uma=is_uma)
            score_res = compute_score(metrics, rules, cfg.scoring)

            payload: dict = {
                "timestamp": datetime.utcnow().isoformat(),
                "ticker": ticker,
                "rules_triggered": [r.name for r in rules if r.triggered],
                "score": score_res.score,
                "severity": score_res.severity,
                "price": metrics.price,
                "change_pct": round(metrics.ret_1d * 100, 2) if metrics.ret_1d is not None else None,
                "vol_ratio": round(metrics.vol_spike_ratio, 2) if metrics.vol_spike_ratio else None,
                "pbv": round(metrics.pbv_today, 2) if metrics.pbv_today else None,
                "pbv_jump": round(metrics.pbv_jump, 2) if metrics.pbv_jump else None,
                "is_uma": is_uma,
                "links": {
                    "idx": f"https://www.idx.co.id/en/listed-companies/company-profiles/"
                           f"?kodeEmiten={ticker.replace('.JK','')}",
                    "chart": f"https://finance.yahoo.com/chart/{ticker}",
                },
            }

            repo.upsert(run_date, ticker, score_res.score, score_res.severity, is_uma, payload)

            if score_res.alert:
                alert_records.append(payload)
                with alerts_file.open("a", encoding="utf-8") as f:
                    f.write(json.dumps(payload) + "\n")
                typer.echo(
                    f"[ALERT] {ticker:10} score={score_res.score:5.1f} "
                    f"severity={score_res.severity:8} rules={payload['rules_triggered']}"
                )
            else:
                typer.echo(f"[OK]    {ticker:10} score={score_res.score:5.1f}")

        except Exception as exc:
            logger.error("screen failed for %s: %s", ticker, exc)
            typer.echo(f"[ERR]   {ticker}: {exc}", err=True)

    if alert_records and notifier:
        notifier.send(alert_records)

    typer.echo(
        f"\nDone. {len(alert_records)} alert(s) → {alerts_file}"
    )


def main() -> None:
    app()
