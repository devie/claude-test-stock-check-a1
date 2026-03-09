# IDX / KSEI Shareholder Scraper

Fetches shareholder composition data (≥1% ownership) for IDX-listed tickers
and persists results as CSV/Parquet with a JSON-lines audit log.

---

## ⚠ Data source realities (read this first)

| Source | Requires login? | Notes |
|--------|----------------|-------|
| **IDX company profile** | No | Public SPA — Playwright needed to execute JS |
| **KSEI AKSes** | Yes (`KSEI_USERNAME` + `KSEI_PASSWORD`) | Primarily an *individual-investor* portfolio portal; company-wide shareholder view is available after login but navigation path varies by portal version |
| **yfinance** (fallback) | No | Data from Yahoo Finance — may be stale or incomplete for IDX tickers |

**robots.txt status (checked 2025-03-09):**
`akses.ksei.co.id` → no `/robots.txt` (returns SPA HTML, no Disallow rules).
`www.ksei.co.id` / `www.idx.co.id` → 404.
No explicit crawl restrictions found. Script uses ≥2.5 s delays + exponential back-off.

---

## Prerequisites

```bash
# Python 3.11+
uv add playwright pandas pyarrow yfinance
# OR
pip install playwright pandas pyarrow yfinance

# Install Chromium browser once
python -m playwright install chromium
```

---

## Environment variables

| Variable | Required | Description |
|----------|----------|-------------|
| `KSEI_USERNAME` | Only for KSEI source | Your AKSes login username |
| `KSEI_PASSWORD` | Only for KSEI source | Your AKSes login password |

Set them in your shell or in a `.env` file (never commit `.env`):

```bash
export KSEI_USERNAME="your_username"
export KSEI_PASSWORD="your_password"
```

---

## CLI flags

```
--issuer    "PT Indosat Ooredoo Hutchison Tbk"   Full name for log metadata
--ticker    ISAT                                  IDX ticker (default: ISAT)
--threshold 1.0                                   Min ownership % to include
--outdir    ./data                                Output directory
--format    csv | parquet                         Output format (default: csv)
--headful                                         Show Chromium window
--timeout   60                                    Page load timeout (seconds)
--dry-run                                         Navigate, verify, screenshot — no output saved
--logfile   ./logs/ksei_scrape.log               Audit log path (JSON-lines, append)
--artifacts ./artifacts                           Debug screenshots / HTML dir
```

---

## Usage examples

```bash
# Basic — IDX public scrape, ISAT, CSV
python ksei_isat_scraper.py --ticker ISAT

# TLKM as Parquet, show browser window
python ksei_isat_scraper.py --ticker TLKM --format parquet --headful

# BBCA with KSEI login
KSEI_USERNAME=xx KSEI_PASSWORD=yy \
  python ksei_isat_scraper.py --ticker BBCA --issuer "PT Bank Central Asia Tbk"

# Dry-run — verify selectors without saving
python ksei_isat_scraper.py --ticker ISAT --dry-run

# Lower threshold — all holders ≥0.5%
python ksei_isat_scraper.py --ticker ISAT --threshold 0.5

# Run via uv
uv run python ksei_isat_scraper.py --ticker ISAT
```

---

## Output files

```
./data/ksei_isat_shareholders_YYYYMMDD_HHMMSS.csv
./logs/ksei_scrape.log        ← JSON-lines audit log (append mode)
./artifacts/idx_ISAT_*.png    ← Debug screenshots on every run
```

### CSV columns

```
issuer, ticker, holder_name, holder_type, shares, percent,
reporting_date, acquired_at, source_url
```

### Audit log entry (JSON, one line per run)

```json
{
  "run_id": "a1b2c3d4-...",
  "issuer": "PT Indosat Ooredoo Hutchison Tbk",
  "ticker": "ISAT",
  "started_at": "2025-03-09T10:00:00+00:00",
  "finished_at": "2025-03-09T10:00:45+00:00",
  "source": "IDX",
  "source_url": "https://www.idx.co.id/...",
  "rows_extracted": 12,
  "rows_after_filter": 8,
  "status": "OK",
  "warnings": [],
  "error": null
}
```

---

## Source-selection logic

```
IDX scrape (Playwright, no login)
  └─ failed / no table found?
       ├─ KSEI_USERNAME + KSEI_PASSWORD set?
       │    └─ KSEI AKSes scrape (Playwright + login)
       │         └─ failed? → yfinance fallback
       └─ credentials not set → yfinance fallback
```

---

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| `playwright not installed` | `pip install playwright && python -m playwright install chromium` |
| IDX returns blank table | Run `--headful` to watch — IDX may have changed tab selectors; check `artifacts/idx_*.png` |
| KSEI login fails | Run `--headful --dry-run` to see the login page; selectors may need updating |
| yfinance returns `None` | Ticker may need `.JK` suffix; check internet connectivity |
| `percent sum > 100` warning | Normal if sources overlap (e.g., mutual fund holdings counted twice) |

---

## Limitations

- **IDX Playwright scrape**: IDX changes its SPA structure periodically. If the shareholder tab selector breaks, check `artifacts/` screenshots and update the `selector` list in `_scrape_idx()`.
- **KSEI AKSes**: The portal is designed for individual investors to view their own portfolios. The issuer shareholder view (company-wide composition) may require navigating to a specific "Emiten" menu that changes with portal updates. Use `--headful` to verify the flow manually first.
- **No captcha solving**: If either site adds captcha challenges, automation will fail. Manual export (download CSV from portal) is the fallback path.
