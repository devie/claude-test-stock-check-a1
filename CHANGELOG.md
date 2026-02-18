# Changelog

All notable changes to Stock Alpha are documented here.

---

## [Unreleased] — 2026-02-19

### Added
- **Market Indices on Dashboard** — row of purple-tinted chips (IHSG `^JKSE`, LQ45 `^JKLQ45`, S&P 500 `^GSPC`, NASDAQ `^IXIC`, NIKKEI `^N225`, HANG SENG `^HSI`, FTSE 100 `^FTSE`, DAX `^GDAXI`) above the watchlist section. Click any chip to load its price chart instantly.
- **Recommendation Summary Box** — auto-computed 3-column card on the Detail page showing BUY / HOLD / SELL signals with bullet-point reasons for short-term (1–3 mo), medium-term (3–12 mo), and long-term (1–3 yr) horizons. Scoring is based on: 52-week price range position, PER valuation, Net Income CAGR, ROE, DER, and Revenue CAGR. Includes investment disclaimer.
- **Screenshot to Clipboard (HD)** — "Screenshot" button on both Dashboard and Detail pages. Captures the entire rendered page as a 2× HD PNG via `html2canvas` and writes it to the system clipboard (`navigator.clipboard.write`). Falls back to downloading `screenshot.png` if the Clipboard API is unavailable (non-HTTPS). Toast confirms success or failure.
- `html2canvas@1.4.1` CDN script added to `templates/alpha/index.html`.
- `.index-chip` CSS class (purple border/color) in `styles.css`.
- `.rec-col` / `.rec-col-header` CSS classes for the recommendation box layout.

### Fixed
- **`_loadDetailChart()` missing bug** — the method was called in four places (period buttons, indicator checkboxes, custom indicator input, initial load) but was never defined, causing the detail page price chart to silently fail. Implemented `_loadDetailChart(ticker)` mirroring `_loadDashChart()`: POSTs to `/api/price-history` with `_detailPeriod` + `_detailIndicators`, renders via `Charts.priceChart()` into `#detail-price-chart`.

### Changed
- Detail page "Save Snapshot" button renamed to **"Save Data"** to distinguish it from the new "Screenshot" button.
- Dashboard section header now includes the "Screenshot" button alongside the page title.

### Files Modified
| File | Summary |
|------|---------|
| `src/stock_checker/alpha/static/alpha/app.js` | `_loadDetailChart()`, `_marketIndices`, `_computeRecommendations()`, `_recLabel()`, `_renderRecommendationBox()`, `screenshotToClipboard()`, index chips UI, recommendation HTML, screenshot buttons |
| `src/stock_checker/alpha/static/alpha/styles.css` | `.index-chip`, `.rec-col`, `.rec-col-header`, `.rec-col ul li` |
| `src/stock_checker/alpha/templates/alpha/index.html` | html2canvas CDN `<script>` tag |

---

## [699ce4e] — Fix all Plotly chart rendering issues (anchor error, empty charts)

## [47c8cad] — Fix DCF/scenario/export, add dashboard price chart with indicators

## [22b179e] — Add currency labels, thousand separators, and ratio suffixes to all number displays

## [b540f70] — Fix: Calculate all ratios from financial statements instead of relying on ticker.info

## [4eaae87] — Alpha Phase 8: Polish - loading states, responsive, error handling
