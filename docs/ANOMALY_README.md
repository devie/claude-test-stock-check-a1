# IDX Anomaly Scanner

Detects unusual price spikes, volume anomalies, PBV jumps, and UMA-listed tickers on the Indonesia Stock Exchange (IDX).

---

## Setup

```bash
# 1. Install dependencies
make dev          # runs uv sync + mkdir data dirs

# 2. Configure secrets
cp .env.example .env
# Edit .env — fill in OHLCDEV_API_KEY, FINNHUB_API_KEY, etc.

# 3. (Optional) Tune thresholds
# Edit config.yml
```

---

## .env Keys

| Key | Required | Description |
|-----|----------|-------------|
| `OHLCDEV_API_KEY` | Yes (if using ohlcdev) | RapidAPI key for OHLC.dev |
| `INVEZGO_API_KEY` | Yes (if using invezgo) | Invezgo API key |
| `FINNHUB_API_KEY` | Yes | Finnhub free-tier key |
| `SLACK_WEBHOOK_URL` | Optional | Slack incoming webhook |
| `TEAMS_WEBHOOK_URL` | Optional | MS Teams connector webhook |
| `SMTP_HOST/USER/PASS` | Optional | For email alerts |
| `ALERT_TO_EMAIL` | Optional | Alert recipient |

---

## config.yml Reference

```yaml
providers:
  price: ohlcdev      # Switch to "invezgo" to use Invezgo instead
  fundamentals: finnhub

storage:
  backend: sqlite     # "parquet" for file-based, no DB required
  sqlite_path: data/anomaly.db
  parquet_dir: data/parquet

rules:
  price_spike:
    min_abs_return: 0.08     # |ret_1d| > max(8%, 3σ)
    sigma_multiplier: 3.0
  volume_spike:
    ratio_threshold: 6.0     # today / median_20d ≥ 6x
  pbv_jump:
    jump_multiplier: 2.0     # pbv_today / median_pbv_60d ≥ 2x
    high_pbv_threshold: 10.0
    high_pbv_delta_pct: 0.50

scoring:
  weights: {price: 40, volume: 30, pbv: 20, uma: 10}
  alert_threshold: 70

alerts:
  channel: console    # console | slack | teams | email
  alerts_dir: data/alerts
```

---

## CLI Examples

```bash
# Fetch OHLCV for tickers (90 days)
uv run idx-anomaly fetch:prices BBCA.JK TLKM.JK BREN.JK

# Fetch fundamentals (BVPS, PBV) from Finnhub
uv run idx-anomaly fetch:fundamentals BBCA.JK TLKM.JK

# Scrape IDX UMA list
uv run idx-anomaly fetch:uma

# Full screen (fetch + compute + score + alert)
uv run idx-anomaly run:screen BBCA.JK TLKM.JK BREN.JK GOTO.JK BMRI.JK

# Override alert threshold
uv run idx-anomaly run:screen BBCA.JK TLKM.JK --alert-threshold 60
```

---

## Cron Samples

```cron
# Every trading day at 16:15 WIB (09:15 UTC) — 15 min after IDX close
15 9 * * 1-5  cd /app && uv run idx-anomaly run:screen \
    BBCA.JK TLKM.JK BREN.JK GOTO.JK BMRI.JK ASII.JK UNVR.JK ISAT.JK \
    >> logs/screen.log 2>&1

# Refresh UMA list at 08:00 UTC on weekdays
0 8 * * 1-5   cd /app && uv run idx-anomaly fetch:uma >> logs/uma.log 2>&1
```

---

## Alert Output

Alerts are written as JSONL to `data/alerts/alerts_YYYY-MM-DD.jsonl`.

Each line is a JSON object:
```json
{
  "timestamp": "2025-02-03T09:15:00",
  "ticker": "BREN.JK",
  "rules_triggered": ["PriceSpike", "VolumeSpike", "UMAFlag"],
  "score": 82.5,
  "severity": "critical",
  "price": 11400,
  "change_pct": 8.06,
  "vol_ratio": 7.3,
  "pbv": 11.4,
  "pbv_jump": 1.9,
  "is_uma": true,
  "links": {
    "idx": "https://www.idx.co.id/...",
    "chart": "https://finance.yahoo.com/chart/BREN.JK"
  }
}
```

---

## Web UI

Navigate to **http://localhost:5000/anomaly/** after running `make run`.

The Anomaly Scanner is also accessible from the **Alpha dashboard nav** via the **Anomaly Scanner** link.

---

## Provider Swap

**Switch price provider to Invezgo:**
```yaml
# config.yml
providers:
  price: invezgo
```
Then set `INVEZGO_API_KEY` in `.env`.

**No external price data?** Replace `OHLCDevProvider` / `InvezgoProvider` by implementing `PriceDataProvider.fetch()` in `providers/base.py` backed by `yfinance` (already a project dependency).

---

## Scoring Formula

```
score = 40 × price_z_norm
      + 30 × vol_ratio_norm
      + 20 × pbv_jump_norm
      + 10 × uma_flag

where each component is clamped [0,1] against a saturation ceiling.
UMAFlag forces score ≥ alert_threshold (70 default).
```

Severity levels: `none` (<40) · `low` (40–69) · `medium` (70–84) · `high` (85–99) · `critical` (UMA or score≥85+UMA)

---

## Optional: Streamlit Dashboard

A richer interactive UI can be built with Streamlit:

```python
# streamlit_app.py (idea sketch)
import streamlit as st, requests
tickers = st.text_input("Tickers (comma-separated)").split(",")
if st.button("Screen"):
    r = requests.post("http://localhost:5000/anomaly/api/screen",
                      json={"tickers": tickers})
    st.dataframe(r.json()["results"])
```

Run with: `streamlit run streamlit_app.py`

---

## Tests

```bash
make test          # Run all idx_anomaly tests
make test-cov      # With coverage report
```

Test coverage:
- `test_indicators.py` — metrics computation, edge cases (short history, empty DF)
- `test_rules.py` — each rule trigger/skip condition
- `test_scoring.py` — score weights, UMA override, severity levels
- `test_uma_parser.py` — HTML parsing with recorded fixture
- `test_providers.py` — parser helpers with no network calls (fixtures only)
