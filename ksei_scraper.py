#!/usr/bin/env python3
"""
ksei_isat_scraper.py — Fetch shareholder data (≥1%) for IDX-listed tickers.

DATA SOURCE HIERARCHY (tried in order)
───────────────────────────────────────
1. IDX company-profile page (PUBLIC, no login)
   URL: https://www.idx.co.id/id/perusahaan-tercatat/
        profil-perusahaan-tercatat/?kodeEmiten=<TICKER>
   Method: Playwright/Chromium — page is a React SPA; must execute JS.

2. KSEI AKSes portal (LOGIN REQUIRED — set KSEI_USERNAME + KSEI_PASSWORD)
   URL: https://akses.ksei.co.id/
   ⚠  AKSes is primarily an individual-investor portfolio service.
      After login, the "Emiten" / issuer section may expose a shareholder
      composition view per company, but the exact navigation path varies
      by portal version. Set --headful to visually verify the flow.

3. yfinance (OFFLINE FALLBACK — may be stale or partial for IDX tickers)

ROBOTS.TXT STATUS (verified 2025-03-09)
────────────────────────────────────────
  akses.ksei.co.id  → /robots.txt returns SPA HTML (no Disallow rules found)
  www.ksei.co.id    → 404
  www.idx.co.id     → 404
  No explicit crawl restrictions documented. Script uses conservative
  2-3 s delays, exponential back-off, max 3 retries per source.

USAGE
─────
  python ksei_isat_scraper.py --ticker ISAT --threshold 1.0
  python ksei_isat_scraper.py --ticker TLKM --format parquet --headful
  python ksei_isat_scraper.py --ticker BBCA --dry-run
  KSEI_USERNAME=xx KSEI_PASSWORD=yy python ksei_isat_scraper.py --ticker ISAT
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

# ── Optional heavy deps (graceful degradation) ───────────────────────────────
try:
    from playwright.sync_api import TimeoutError as PwTimeout, sync_playwright
    HAS_PW = True
except ImportError:
    HAS_PW = False

try:
    import yfinance as yf
    HAS_YF = True
except ImportError:
    HAS_YF = False

try:
    import pyarrow  # noqa: F401
    HAS_PA = True
except ImportError:
    HAS_PA = False

# ── Constants ─────────────────────────────────────────────────────────────────
_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)
IDX_URL = (
    "https://www.idx.co.id/id/perusahaan-tercatat/"
    "profil-perusahaan-tercatat/?kodeEmiten={ticker}"
)
KSEI_URL  = "https://akses.ksei.co.id/"
MAX_RETRY = 3
BASE_WAIT = 2.5   # seconds between requests (respectful baseline)

_SCHEMA = ["issuer", "ticker", "holder_name", "holder_type",
           "shares", "percent", "reporting_date", "acquired_at", "source_url"]


# ══════════════════════════════════════════════════════════════════════════════
# Audit log helpers
# ══════════════════════════════════════════════════════════════════════════════
def _new_ctx(ticker: str, issuer: str) -> dict:
    return dict(run_id=str(uuid.uuid4()), issuer=issuer, ticker=ticker,
                started_at=datetime.now(timezone.utc).isoformat(),
                finished_at=None, source=None, source_url=None,
                rows_extracted=0, rows_after_filter=0,
                status="RUNNING", warnings=[], error=None)


def _write_log(ctx: dict, log_path: Path, status: str, **kw) -> None:
    ctx.update(kw)
    ctx["status"] = status
    ctx["finished_at"] = datetime.now(timezone.utc).isoformat()
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with open(log_path, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(ctx, default=str) + "\n")


# ══════════════════════════════════════════════════════════════════════════════
# Number parsing  (handles Indonesian "1.234.567,89" AND US "1,234,567.89")
# ══════════════════════════════════════════════════════════════════════════════
def _num(s: str) -> float:
    s = str(s).strip().replace("%", "").replace(" ", "")
    # Detect Indonesian thousands-dot / decimal-comma
    if s.count(".") > 1 or (
        s.count(".") == 1 and s.count(",") == 1
        and s.rindex(".") < s.rindex(",")
    ):
        s = s.replace(".", "").replace(",", ".")
    else:
        s = s.replace(",", "")
    try:
        return float(s)
    except ValueError:
        return float("nan")


# ══════════════════════════════════════════════════════════════════════════════
# Column-mapping heuristics: raw SPA table → standard schema
# ══════════════════════════════════════════════════════════════════════════════
def _map_columns(raw: pd.DataFrame) -> pd.DataFrame:
    """Best-effort mapping of raw column names to standard schema."""
    mapping: dict[str, str] = {}
    for col in raw.columns:
        lc = str(col).lower()
        if any(k in lc for k in ("nama", "holder", "pemegang", "name")):
            mapping[col] = "holder_name"
        elif any(k in lc for k in ("tipe", "jenis", "type", "kategori")):
            mapping[col] = "holder_type"
        elif any(k in lc for k in ("saham", "share", "jumlah")) and "pct" not in lc and "%" not in lc:
            mapping[col] = "shares"
        elif any(k in lc for k in ("persen", "percent", "%", "porsi")):
            mapping[col] = "percent"
        elif any(k in lc for k in ("tanggal", "date", "report")):
            mapping[col] = "reporting_date"

    out = raw.rename(columns=mapping)

    # Fallback: if holder_name still missing, use first text column
    if "holder_name" not in out.columns:
        text_cols = [c for c in out.columns if out[c].dtype == object]
        if text_cols:
            out = out.rename(columns={text_cols[0]: "holder_name"})

    # Fallback: if percent missing, look for column with values 0–100
    if "percent" not in out.columns:
        for col in out.columns:
            nums = pd.to_numeric(out[col].astype(str).str.replace("%", ""), errors="coerce")
            if nums.between(0, 100).sum() > len(out) * 0.5:
                out = out.rename(columns={col: "percent"})
                break

    for col in ("holder_type", "shares", "percent", "reporting_date"):
        if col not in out.columns:
            out[col] = None

    out["percent"] = out["percent"].apply(_num)
    out["shares"]  = out["shares"].apply(lambda v: _num(v) if pd.notna(v) else float("nan"))
    return out


# ══════════════════════════════════════════════════════════════════════════════
# Source 1 — IDX company profile (public)
# ══════════════════════════════════════════════════════════════════════════════
def _scrape_idx(
    ticker: str, headful: bool, timeout: int,
    dry_run: bool, artifacts: Path,
) -> pd.DataFrame | None:
    if not HAS_PW:
        print("[SKIP] playwright not installed — IDX source unavailable")
        return None

    url = IDX_URL.format(ticker=ticker)
    print(f"[IDX] → {url}")

    for attempt in range(1, MAX_RETRY + 1):
        try:
            with sync_playwright() as pw:
                browser = pw.chromium.launch(headless=not headful)
                page = browser.new_context(
                    user_agent=_UA, viewport={"width": 1280, "height": 900},
                    extra_http_headers={"Accept-Language": "id-ID,id;q=0.9,en;q=0.8"},
                ).new_page()

                page.goto(url, timeout=timeout * 1000, wait_until="networkidle")
                time.sleep(BASE_WAIT)

                # Try to activate the "Pemegang Saham" tab (may be named differently)
                for selector in [
                    "text=Pemegang Saham", "text=Shareholders",
                    "text=Komposisi", "a[href*='holder']",
                    "[role='tab']:has-text('Pemegang')",
                ]:
                    try:
                        el = page.locator(selector).first
                        if el.is_visible(timeout=3_000):
                            el.click()
                            time.sleep(BASE_WAIT)
                            print(f"[IDX] Clicked tab: {selector}")
                            break
                    except Exception:
                        pass

                # Screenshot for debugging / dry-run evidence
                artifacts.mkdir(parents=True, exist_ok=True)
                ss = artifacts / f"idx_{ticker}_{datetime.now():%Y%m%d_%H%M%S}.png"
                page.screenshot(path=str(ss), full_page=False)
                print(f"[IDX] Screenshot → {ss}")

                if dry_run:
                    tables_count = page.locator("table").count()
                    print(f"[DRY-RUN][IDX] tables found = {tables_count}")
                    browser.close()
                    return None

                # Extract first table containing % values
                df = None
                for tbl in page.locator("table").all():
                    html = tbl.inner_html()
                    if "%" not in html or len(html) < 150:
                        continue
                    rows = [
                        [td.inner_text().strip() for td in tr.locator("td,th").all()]
                        for tr in tbl.locator("tr").all()
                    ]
                    rows = [r for r in rows if any(c for c in r)]
                    if len(rows) >= 2:
                        header, *body = rows
                        df = pd.DataFrame(body, columns=header[: len(body[0])])
                        print(f"[IDX] Table: {len(df)} rows, cols={list(df.columns)}")
                        break

                browser.close()
                if df is not None and not df.empty:
                    return df

                print("[IDX] No usable shareholder table found")
                return None

        except PwTimeout:
            print(f"[IDX] Timeout (attempt {attempt}/{MAX_RETRY})")
        except Exception as exc:
            print(f"[IDX] Error (attempt {attempt}/{MAX_RETRY}): {exc}")

        if attempt < MAX_RETRY:
            wait = BASE_WAIT * (2 ** attempt)
            print(f"[IDX] Back-off {wait:.0f}s …")
            time.sleep(wait)

    return None


# ══════════════════════════════════════════════════════════════════════════════
# Source 2 — KSEI AKSes (login required)
# ══════════════════════════════════════════════════════════════════════════════
def _scrape_ksei(
    ticker: str, headful: bool, timeout: int,
    dry_run: bool, artifacts: Path,
) -> pd.DataFrame | None:
    user = os.environ.get("KSEI_USERNAME", "").strip()
    pwd  = os.environ.get("KSEI_PASSWORD", "").strip()
    if not (user and pwd):
        print("[SKIP] KSEI_USERNAME / KSEI_PASSWORD not set — skipping KSEI")
        return None
    if not HAS_PW:
        print("[SKIP] playwright not installed — KSEI source unavailable")
        return None

    print(f"[KSEI] Login as {user[:3]}*** …")
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=not headful)
            page = browser.new_context(user_agent=_UA, viewport={"width": 1280, "height": 900}).new_page()
            page.goto(KSEI_URL, timeout=timeout * 1000, wait_until="networkidle")
            time.sleep(BASE_WAIT)

            # Fill login form (React SPA — wait for fields)
            page.wait_for_selector(
                "input[type='text'], input[name*='user'], input[id*='user'], input[placeholder*='username']",
                timeout=timeout * 1000,
            )
            page.locator("input[type='text']").first.fill(user)
            time.sleep(0.5)
            page.locator("input[type='password']").first.fill(pwd)
            time.sleep(0.5)
            page.locator(
                "button[type='submit'], button:has-text('Login'), button:has-text('Masuk')"
            ).first.click()
            page.wait_for_load_state("networkidle", timeout=timeout * 1000)
            time.sleep(BASE_WAIT)

            artifacts.mkdir(parents=True, exist_ok=True)
            page.screenshot(path=str(artifacts / f"ksei_login_{datetime.now():%Y%m%d_%H%M%S}.png"))

            if dry_run:
                print("[DRY-RUN][KSEI] Login attempted — check screenshot in artifacts/")
                browser.close()
                return None

            # Navigate to issuer shareholder page — try known URL patterns
            source_url = KSEI_URL
            for path in [
                f"{KSEI_URL}securities/shareholder?issuer={ticker}",
                f"{KSEI_URL}issuer/{ticker}",
                f"{KSEI_URL}emiten/{ticker}/pemegang-saham",
            ]:
                try:
                    page.goto(path, timeout=30_000, wait_until="networkidle")
                    time.sleep(BASE_WAIT)
                    if "%" in page.content() and ticker.upper() in page.content().upper():
                        source_url = path
                        print(f"[KSEI] Data page: {path}")
                        break
                except Exception:
                    pass

            # Extract table
            df = None
            for tbl in page.locator("table").all():
                html = tbl.inner_html()
                if "%" not in html or len(html) < 100:
                    continue
                rows = [
                    [td.inner_text().strip() for td in tr.locator("td,th").all()]
                    for tr in tbl.locator("tr").all()
                ]
                rows = [r for r in rows if any(c for c in r)]
                if len(rows) >= 2:
                    header, *body = rows
                    df = pd.DataFrame(body, columns=header[:len(body[0])])
                    break

            page.screenshot(path=str(artifacts / f"ksei_{ticker}_{datetime.now():%Y%m%d_%H%M%S}.png"))
            browser.close()

            if df is not None and not df.empty:
                return df
            print("[KSEI] No shareholder table found after login")
            return None

    except Exception as exc:
        print(f"[KSEI] Error: {exc}")
        return None


# ══════════════════════════════════════════════════════════════════════════════
# Source 3 — yfinance fallback
# ══════════════════════════════════════════════════════════════════════════════
def _scrape_yfinance(ticker: str) -> pd.DataFrame | None:
    if not HAS_YF:
        print("[SKIP] yfinance not installed")
        return None
    jk = ticker if "." in ticker else ticker + ".JK"
    print(f"[yfinance] institutional_holders for {jk}")
    try:
        ih = yf.Ticker(jk).institutional_holders
        if ih is None or ih.empty:
            return None
        ih = ih.copy()
        ih.columns = [c.lower().replace(" ", "_") for c in ih.columns]
        pct_col  = next((c for c in ih.columns if "pct" in c and "change" not in c), None)
        shr_col  = next((c for c in ih.columns if "share" in c and "pct" not in c), None)
        hld_col  = next((c for c in ih.columns if "holder" in c), ih.columns[0])
        dat_col  = next((c for c in ih.columns if "date" in c or "report" in c), None)
        df = pd.DataFrame()
        df["holder_name"]    = ih[hld_col].astype(str)
        df["holder_type"]    = "Institution"
        df["shares"]         = ih[shr_col].apply(_num) if shr_col else float("nan")
        df["reporting_date"] = pd.to_datetime(ih[dat_col], errors="coerce") if dat_col else None
        if pct_col:
            vals = ih[pct_col].apply(_num)
            # yfinance sometimes returns decimal (0.052) instead of percent (5.2)
            df["percent"] = vals.apply(lambda v: v * 100 if abs(v) < 1.5 else v)
        else:
            df["percent"] = float("nan")
        return df
    except Exception as exc:
        print(f"[yfinance] Error: {exc}")
        return None


# ══════════════════════════════════════════════════════════════════════════════
# Validation
# ══════════════════════════════════════════════════════════════════════════════
def _validate(df: pd.DataFrame) -> list[str]:
    warns: list[str] = []
    pct_sum = df["percent"].sum()
    if pct_sum > 100 + 1e-3:
        warns.append(f"percent sum={pct_sum:.2f} > 100 (possible overlap or data error)")
    if (pd.to_numeric(df["shares"], errors="coerce").fillna(0) < 0).any():
        warns.append("negative share counts detected")
    if len(df) == 0:
        warns.append("rows_after_filter = 0 — threshold may be too high")
    return warns


# ══════════════════════════════════════════════════════════════════════════════
# CLI entry point
# ══════════════════════════════════════════════════════════════════════════════
def main() -> None:
    ap = argparse.ArgumentParser(
        description="Fetch IDX/KSEI shareholder data (≥1%) with audit logging",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument("--issuer",    default="", help="Full issuer name (for log metadata)")
    ap.add_argument("--ticker",    default="ISAT", help="IDX ticker, e.g. ISAT or ISAT.JK")
    ap.add_argument("--threshold", type=float, default=1.0, help="Min ownership %% (default 1.0)")
    ap.add_argument("--outdir",    default="./data", help="Output directory (default ./data)")
    ap.add_argument("--format",    choices=["csv", "parquet"], default="csv")
    ap.add_argument("--headful",   action="store_true", help="Show Chromium window")
    ap.add_argument("--timeout",   type=int, default=60, help="Page load timeout, seconds")
    ap.add_argument("--dry-run",   action="store_true", dest="dry_run",
                    help="Navigate and verify selectors; do not save output")
    ap.add_argument("--logfile",   default="./logs/ksei_scrape.log")
    ap.add_argument("--artifacts", default="./artifacts",
                    help="Dir for debug screenshots / HTML snapshots")
    args = ap.parse_args()

    ticker    = args.ticker.upper().replace(".JK", "")
    issuer    = args.issuer or ticker
    outdir    = Path(args.outdir)
    log_path  = Path(args.logfile)
    artifacts = Path(args.artifacts)

    run = _new_ctx(ticker, issuer)
    print(f"\n{'='*62}")
    print(f"  IDX/KSEI Shareholder Scraper  run_id={run['run_id'][:8]}")
    print(f"  Ticker={ticker}  Threshold={args.threshold}%  Format={args.format}")
    print(f"{'='*62}\n")

    # ── Try sources ───────────────────────────────────────────────────────────
    raw_df: pd.DataFrame | None = None
    source: str = ""
    source_url: str = ""

    raw = _scrape_idx(ticker, args.headful, args.timeout, args.dry_run, artifacts)
    if raw is not None and not raw.empty:
        source, source_url = "IDX", IDX_URL.format(ticker=ticker)
        raw_df = raw

    if raw_df is None:
        raw = _scrape_ksei(ticker, args.headful, args.timeout, args.dry_run, artifacts)
        if raw is not None and not raw.empty:
            source, source_url = "KSEI", KSEI_URL
            raw_df = raw

    if raw_df is None:
        raw = _scrape_yfinance(ticker)
        if raw is not None and not raw.empty:
            source, source_url = "yfinance", f"yfinance:{ticker}.JK"
            raw_df = raw
            run["warnings"].append("Data from yfinance fallback — may be stale/incomplete")

    if raw_df is None or (not args.dry_run and raw_df.empty):
        msg = "All data sources exhausted — no shareholder data retrieved."
        print(f"\n[FAIL] {msg}")
        _write_log(run, log_path, "FAILED", error=msg)
        sys.exit(1)

    if args.dry_run:
        print(f"\n[DRY-RUN] source={source or 'none'}, rows_raw={len(raw_df) if raw_df is not None else 0}")
        _write_log(run, log_path, "DRY_RUN", source=source, source_url=source_url,
                   rows_extracted=len(raw_df) if raw_df is not None else 0)
        return

    # ── Normalise, filter, validate ───────────────────────────────────────────
    df = _map_columns(raw_df)
    rows_raw = len(df)

    df["percent"] = pd.to_numeric(df["percent"], errors="coerce")
    df = df.dropna(subset=["percent"])
    df = df[df["percent"] >= args.threshold].copy()

    warns = _validate(df)
    run["warnings"].extend(warns)
    for w in warns:
        print(f"[WARN] {w}")

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    df["issuer"]       = issuer
    df["ticker"]       = ticker
    df["acquired_at"]  = datetime.now(timezone.utc).isoformat()
    df["source_url"]   = source_url

    # Reorder to schema
    present = [c for c in _SCHEMA if c in df.columns]
    df = df[present]

    # ── Persist ───────────────────────────────────────────────────────────────
    fmt = args.format
    if fmt == "parquet" and not HAS_PA:
        print("[WARN] pyarrow not installed — writing CSV instead")
        fmt = "csv"

    outdir.mkdir(parents=True, exist_ok=True)
    stem = f"ksei_{ticker.lower()}_shareholders_{ts}"
    out  = outdir / (stem + (".parquet" if fmt == "parquet" else ".csv"))
    df.to_parquet(out, index=False) if fmt == "parquet" else df.to_csv(out, index=False)

    # ── Summary ───────────────────────────────────────────────────────────────
    print(f"\n{'─'*62}")
    print(f"  Source         : {source}")
    print(f"  Rows extracted : {rows_raw}")
    print(f"  Rows ≥{args.threshold}%     : {len(df)}")
    print(f"  Output         : {out}")
    if run["warnings"]:
        print(f"  Warnings       : {'; '.join(run['warnings'])}")
    print(f"{'─'*62}\n")

    _write_log(run, log_path, "OK", source=source, source_url=source_url,
               rows_extracted=rows_raw, rows_after_filter=len(df))


if __name__ == "__main__":
    main()
