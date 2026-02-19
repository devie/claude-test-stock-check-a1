# StockAlpha — Product Roadmap

**Last Updated:** 2026-02-20
**Status:** Post-Phase-2 (scoring, valuation models, H2H, industry cards complete)

---

## Tier 1: Quick Wins (1–2 weeks)

Targeted improvements with high UX impact and low implementation risk.

| ID | Feature | Description | Files | Status |
|----|---------|-------------|-------|--------|
| Q1 | Detail page tab bar | 4-tab layout: Overview / Financials / Trends / Valuation | `app.js` | ✅ Done |
| Q2 | N/A row filtering | Hide null ratio rows in Overview tab cards; "Show all" toggle | `app.js` | ✅ Done |
| Q3 | Technology sector | Add `teknologi` to INDUSTRY_MAP, INDUSTRY_CONFIG, calc_specific_ratios | `calculations/industry.py` | ✅ Done |
| Q4 | Mining Gross Margin | Add `Gross Margin (%)` to energi_pertambangan specific_ratios | `calculations/industry.py` | ✅ Done |
| Q5 | Valuation synthesis | Weighted fair value panel at top of Model page | `app.js` | ✅ Done |
| Q6 | Score gauge drill-down | Click gauge label → expand sub-metric breakdown panel | `app.js` | ✅ Done |
| Q7 | H2H quick-launch | ⇄ Compare H2H button on Detail page price summary | `app.js` | ✅ Done |
| Q8 | Sensitivity heat map | Color-coded HTML table replacing Plotly heatmap | `app.js` | ✅ Done |

---

## Tier 2: Medium Impact (1–2 months)

Features that add meaningful analytical depth or expand the user base.

| ID | Feature | Description | Priority |
|----|---------|-------------|----------|
| M1 | Screener page | Multi-factor filter (PER < X, ROE > Y, sector = Z) with sortable table | High |
| M2 | Watchlist price alerts | Email/browser notification when price crosses threshold | High |
| M3 | Earnings calendar | IDX & US earnings dates widget with EPS surprise history | Medium |
| M4 | Sector-aware scoring | Calibrate normalization ranges per sector (banks skip DER, tech raise GPM) | Medium |
| M5 | Excel (XLSX) export | Export comparison/snapshot data to .xlsx | Medium |
| M6 | Portfolio P&L chart | Realized/unrealized P&L breakdown per holding | Medium |
| M7 | Peer auto-discovery | Dynamic peer selection via sector/market-cap similarity | Medium |
| M8 | Note search & filter | Full-text search + tag filter for analyst notes | Low |
| M9 | Dark/light theme toggle | CSS variable swap with localStorage persistence | Low |
| M10 | Snapshot history chart | Plot saved snapshots over time (ratio trend tracker) | Low |

---

## Tier 3: Strategic Upgrades (3–6 months)

Institutional-grade features requiring significant architecture changes.

| ID | Feature | Description | Effort |
|----|---------|-------------|--------|
| S1 | Real-time price streaming | WebSocket integration (e.g., Polygon.io / TradingView) | High |
| S2 | Analyst consensus API | Price target range, Buy/Hold/Sell consensus from broker data | High |
| S3 | Insider transaction tracker | IDX disclosure + SEC Form 4 scraper | High |
| S4 | Factor model attribution | Fama-French 3-factor or 5-factor portfolio attribution | High |
| S5 | Mobile PWA | Service worker, offline cache, responsive layout overhaul | High |
| S6 | Multi-user workspace | Team accounts, shared watchlists, comment threads on notes | High |
| S7 | AI narrative generation | GPT/Claude-generated equity research summary per ticker | Medium |
| S8 | Options flow monitor | Unusual options activity scanner (US markets) | Medium |

---

## Architecture Notes

### Near-term (Q1 2026)
- All Quick Wins (Q1–Q8) are frontend-only or minimal backend changes.
- Technology sector (Q3/Q4) adds ~100 lines to `calculations/industry.py`.
- Valuation synthesis (Q5) adds a frontend-only `_loadValuationSynthesis()` method.

### Medium-term (Q2–Q3 2026)
- Screener (M1) requires a new `/api/screener` endpoint with database-cached ratio snapshots.
- Alerts (M2) requires a background job scheduler (APScheduler or Celery).
- XLSX export (M5) requires `openpyxl` dependency.

### Long-term (Q4 2026+)
- Real-time streaming (S1) requires WebSocket infrastructure (Flask-SocketIO or separate service).
- Multi-user (S6) requires auth system (Flask-Login / JWT) + user-scoped database tables.
- Factor attribution (S4) requires historical return data and linear regression engine.

---

## Completed Features (Archive)

| Feature | Completed | Description |
|---------|-----------|-------------|
| Scoring engine | Phase 2 | Quality / Valuation / Risk scores + composite + recommendation |
| PBV valuation | Phase 2 | Justified PBV model for banks |
| DDM (Gordon Growth) | Phase 2 | Dividend discount model |
| ROE Growth model | Phase 2 | Sustainable growth model |
| H2H comparison | Phase 2 | Head-to-head with score gauges + verdict |
| Industry cards | Phase 2 | 8-sector detection + bilingual thesis + valuation bands |
| Technical signals | Phase 2 | RSI / MACD / SMA interpretation card |
| Peer H2H quick-link | Phase 2 | Peer tickers in industry card launch H2H directly |
| English UI labels | Phase 2 | All UI labels in English (EN/ID thesis preserved) |
| Dashboard default | Phase 2 | Default ticker `^JKSE` (IHSG chart on load) |
| Anomaly detection | Phase 1 | Statistical z-score alerts for ratio outliers |
| Markdown notes | Phase 1 | Live-preview editor with toolbar shortcuts |
| Watchlists | Phase 1 | Portfolio watchlist management |
| Snapshot history | Phase 1 | Save/compare ratio snapshots |
| Export (CSV/JSON/PDF) | Phase 1 | Multi-format comparison export |
| Linear projection | Phase 1 | Least-squares extrapolation for financial metrics |
