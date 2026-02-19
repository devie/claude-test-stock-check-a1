# StockAlpha — Senior Product Architect Review

**Review Date:** 2026-02-20
**Reviewer:** Senior Product Architect (AI-assisted)
**Version Reviewed:** Post-Phase-2 (scoring engine, valuation models, H2H, industry cards, bilingual thesis complete)

---

## 1. Current State Assessment

### 1.1 Strengths
- **Solid multi-page SPA architecture** — Router-based navigation with clean render/render-skeleton lifecycle.
- **Comprehensive backend stack** — Flask + yfinance + SQLite; well-separated into calculations / services / routes layers.
- **Industry intelligence** — 8-sector detection engine with bilingual (EN/ID) investment thesis, valuation bands, and peer H2H links.
- **Scoring engine** — Quality / Valuation / Risk composite scores with auto recommendation (Strong Buy → Avoid).
- **Valuation depth** — DCF + Scenario + Sensitivity + PBV + DDM + ROE Growth models, all in one page.
- **H2H comparison** — Side-by-side ratio comparison with score gauges, industry analysis, and verdict panel.
- **Technical signals** — RSI / MACD / SMA interpretations rendered on detail page post chart load.
- **Data export** — CSV / JSON / PDF export + screenshot-to-clipboard for all major pages.
- **Markdown note editor** — Live preview, toolbar shortcuts, Ctrl+B/I, tag support.

### 1.2 Weaknesses
- **Detail page is a single long scroll** — No section tabs; user must scroll past 10+ cards to reach financials.
- **Ratio cards show N/A rows** — Unavailable metrics clutter the overview; no way to hide them.
- **Score gauges are opaque** — Composite score visible but no drill-down showing which sub-metrics drove it.
- **Valuation models are disconnected** — Four independent models return separate intrinsic values with no synthesis.
- **H2H requires full navigation** — No quick-launch from the detail page; user must go to Compare tab manually.
- **Sensitivity matrix is Plotly-rendered** — Heavy dependency; color-coded HTML table would be faster and more readable.
- **Technology sector missing** — Tech companies (GOTO, BUKA, MSFT, AAPL) fall through to 'General' classification.
- **Mining lacks Gross Margin** — energi_pertambangan ratios omit GPM, which is a key commodity cycle indicator.
- **No `_pendingModelTicker`** — Navigating from detail → model always requires re-entering the ticker.

### 1.3 Gaps vs. Institutional-Grade Tools

| Feature | Current | Institutional Standard |
|---------|---------|----------------------|
| Peer benchmarking | Static list | Dynamic screener-based peers |
| Earnings calendar | Not implemented | Real-time EPS surprise alerts |
| Insider transactions | Not implemented | SEC/IDX filing scraper |
| Price target consensus | Not implemented | Analyst consensus range |
| Portfolio attribution | Basic | Factor-based attribution |
| Real-time data | yfinance (delayed) | WebSocket streaming |
| Screener | Not implemented | Multi-factor filter engine |
| Alert system | Not implemented | Price/ratio threshold push alerts |

---

## 2. Dashboard Evaluation

### 2.1 Detail Page (renderDetail)
**Current structure (single scroll):**
- Price summary → Recommendation → Score gauges → Price chart → Tech signals → Highlights → 3 ratio cards → Anomalies → Industry card → Trend charts → Financial statements

**Issues:**
- Financial statements are buried 10+ cards deep.
- Price chart and trend charts are on the same scroll — context switching is difficult.
- Industry card loads async but is mid-page; user may scroll past it before it renders.

**Recommendation:** 4-tab layout:
- **Overview** — Price summary, Score gauges, Highlights, 3 ratio cards (N/A filtered), Anomalies
- **Financials** — Statement tabs (Income / Balance / CF / Quarterly) + full ratio table
- **Trends** — Price chart + period/indicator controls + Trend charts + Technical signals
- **Valuation** — Industry card + "Open Valuation Models" button

### 2.2 Compare Page
**Strengths:** Tab switcher (Multi / H2H) works cleanly. H2H verdict panel is informative.
**Gap:** No way to launch H2H from the Detail page with the current ticker pre-filled.

### 2.3 Valuation (Model) Page
**Strengths:** Six models cover DCF, Scenario, Sensitivity, PBV, DDM, ROE.
**Gaps:**
- Each model returns a standalone intrinsic value — no weighted synthesis.
- Sensitivity matrix uses Plotly (slow) — HTML heat map is more performant.
- Ticker must be re-entered manually when navigating from detail page.

---

## 3. Sector Metric Gaps

| Sector | Missing Metrics | Impact |
|--------|----------------|--------|
| Technology | All (sector not detected) | GOTO, BUKA, MSFT fall to General |
| Energy/Mining | Gross Margin (%) | Key commodity-cycle indicator |
| Banking | Loan-to-Deposit Ratio | Standard banking solvency metric |
| Healthcare | R&D/Revenue | Biotech pipeline quality signal |
| Real Estate | Cap Rate, NAV discount | REIT-specific valuation |

---

## 4. Valuation Unification Proposal

**Problem:** User runs DCF (e.g., intrinsic = 15,000), PBV (intrinsic = 12,000), DDM (intrinsic = 14,000) — no summary.

**Solution:** Weighted Fair Value synthesis panel at top of Model page:
```
Model        Intrinsic   Weight   Contribution
DCF          15,000      40%      6,000
PBV          12,000      35%      4,200
DDM          14,000      25%      3,500
─────────────────────────────────────────────
Weighted FV  13,700
Current      10,500      Upside   +30.5% ✅ Undervalued
```

Weights auto-set per sector (banks: PBV heavy; dividend stocks: DDM heavy; growth: DCF heavy).

---

## 5. UI/UX Recommendations

### 5.1 Quick Wins (1–2 weeks)
1. **Tab bar on Detail page** — reduces scroll fatigue significantly.
2. **N/A row filtering** on ratio cards with "Show all" toggle.
3. **Score gauge drill-down** — click label to expand sub-metric breakdown.
4. **Valuation synthesis panel** — weighted fair value above model grids.
5. **⇄ H2H button** on detail page price summary header.
6. **Sensitivity heat map** — replace Plotly with color-coded HTML table.
7. **`_pendingModelTicker`** — auto-fill model page ticker from detail navigation.

### 5.2 Medium Impact (1–2 months)
- Screener page with multi-factor filter
- Earnings calendar widget
- Portfolio P&L attribution chart
- Export to Excel (XLSX)
- Dark/light theme toggle
- Notification system for price/ratio alerts

### 5.3 Strategic (3–6 months)
- Real-time price WebSocket integration
- Analyst consensus API (Bloomberg / Refinitiv)
- Insider transaction tracker
- Factor model attribution (Fama-French 3-factor)
- Mobile-responsive PWA
- Multi-user / team workspace

---

## 6. Cross-Sector Scoring Calibration

**Current normalization ranges (scores.py):**
- ROE: 0–30% → 0–100 (good for most sectors)
- GPM: 0–60% → 0–100 (too low for tech — typical SaaS GPM is 70–85%)
- DER: 0–3x → 0–100 (too strict for banks where DER >10x is normal)

**Recommendations:**
- Sector-aware normalization ranges in `calc_quality_score()`.
- Banks: skip DER from risk score (use CAR / NPL instead).
- Tech: raise GPM ceiling to 90%, add R&D/Revenue as quality metric.
- Real Estate: use NAV discount instead of PBV for valuation score.

---

## 7. Missing Institutional Features

| Feature | Priority | Effort |
|---------|----------|--------|
| Screener (filter by ratio ranges) | High | Medium |
| Watchlist price alerts | High | Low |
| Earnings calendar | Medium | Medium |
| Insider activity feed | Medium | High |
| Analyst consensus | Medium | High |
| Factor attribution | Low | High |
| Excel export | Low | Low |
| Multi-currency P&L | Low | Medium |

---

## 8. Summary Score Card

| Dimension | Score | Comment |
|-----------|-------|---------|
| Data Coverage | 7/10 | yfinance covers 80% of needed fields |
| UI/UX | 6/10 | Functional but single-scroll detail page is fatiguing |
| Analysis Depth | 8/10 | 6 valuation models + scoring is strong |
| Industry Intelligence | 7/10 | 8 sectors; Tech missing; Mining incomplete |
| Performance | 7/10 | Async loading good; Plotly sensitivity is heavy |
| Institutional Readiness | 4/10 | Missing screener, alerts, real-time, consensus |
| **Overall** | **6.5/10** | **Solid MVP; needs UI polish + institutional features** |
