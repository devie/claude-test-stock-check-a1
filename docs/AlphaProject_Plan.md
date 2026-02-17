# Stock Review Intelligence - Implementation Plan

## Context

Expanding the existing Stock Checker app (`stock.zuhdi.id`) with a comprehensive "Stock Review Intelligence" module accessible at `stock.zuhdi.id/alpha/`. The existing app is a simple Flask + yfinance + Plotly.js single-ticker analyzer. The new module adds multi-ticker comparison, financial statement analysis, DCF/scenario modelling, watchlist persistence, and export capabilities.

---

## Architecture Decision

**Flask Blueprint** registered on the existing app with `url_prefix="/alpha"`. No separate process, no tunnel changes. The existing `GET /` and `POST /api/analyze` remain untouched.

**Integration point** (only existing file modified):
- `src/stock_checker/app.py` - add 2 lines to register the Blueprint

---

## Project Structure (New Files)

```
src/stock_checker/alpha/              # NEW subpackage
    __init__.py                       # Blueprint factory + DB init
    routes/
        __init__.py
        dashboard.py                  # GET /alpha/ (SPA shell)
        comparison.py                 # POST /alpha/api/compare
        financials.py                 # POST /alpha/api/financials
        trends.py                     # POST /alpha/api/trends
        modelling.py                  # POST /alpha/api/model/*
        portfolio.py                  # /alpha/api/watchlists/*, notes/*, snapshots/*
        export.py                     # POST /alpha/api/export/*
    services/
        __init__.py
        data_fetcher.py               # yfinance wrapper + TTL cache
        comparison.py                 # Multi-ticker comparison logic
        financials.py                 # Statement parsing + ratio calc
        trends.py                     # YoY/QoQ trend analysis
        modelling.py                  # DCF, scenarios, sensitivity
        portfolio.py                  # Watchlist/notes CRUD
        export.py                     # CSV, JSON, PDF generation
    models/
        __init__.py
        database.py                   # SQLAlchemy db instance
        schemas.py                    # All DB models (6 tables)
    calculations/
        __init__.py
        ratios.py                     # PER, PBV, ROE, ROA, NPM, GPM, DER, etc.
        growth.py                     # CAGR, YoY, QoQ calculations
        valuation.py                  # DCF, EV/EBITDA computation
        anomaly.py                    # Anomaly detection (z-score, specific checks)
    templates/alpha/
        index.html                    # Main SPA shell
        export_pdf.html               # PDF export template
    static/alpha/
        styles.css                    # Dark theme CSS
        app.js                        # Main SPA: router + page renderers
        components/
            router.js                 # Hash-based SPA router
            charts.js                 # Plotly chart builders
            tables.js                 # Table rendering helpers
            forms.js                  # Editable form helpers for modelling
```

---

## Database (SQLite via Flask-SQLAlchemy)

File: `instance/alpha.db` (auto-created)

**6 tables:**
1. `watchlist` - id, name, description, timestamps
2. `watchlist_item` - id, watchlist_id (FK), ticker, category, added_at
3. `analysis_note` - id, ticker, title, content, tags, timestamps
4. `ratio_snapshot` - id, ticker, snapshot_date, data_json, created_at
5. `valuation_result` - id, ticker, model_type, assumptions_json, results_json, created_at
6. `comparison_session` - id, name, tickers_json, results_json, created_at

---

## API Endpoints

### Data APIs
| Method | Path | Purpose |
|--------|------|---------|
| POST | `/alpha/api/compare` | Compare up to 8 tickers across metric categories |
| POST | `/alpha/api/financials` | Financial statements + ratios + anomalies for 1 ticker |
| POST | `/alpha/api/trends` | YoY/QoQ trend analysis for 1 ticker |
| POST | `/alpha/api/model/dcf` | DCF valuation with user assumptions |
| POST | `/alpha/api/model/scenario` | Bull/base/bear scenario analysis |
| POST | `/alpha/api/model/sensitivity` | 2D sensitivity matrix |
| POST | `/alpha/api/model/projection` | Linear projection with confidence bands |

### Persistence APIs
| Method | Path | Purpose |
|--------|------|---------|
| GET/POST | `/alpha/api/watchlists` | List/create watchlists |
| GET/PUT/DELETE | `/alpha/api/watchlists/<id>` | CRUD single watchlist |
| POST/DELETE | `/alpha/api/watchlists/<id>/items` | Add/remove ticker |
| GET/POST | `/alpha/api/notes` | List/create notes |
| PUT/DELETE | `/alpha/api/notes/<id>` | Update/delete note |
| POST/GET | `/alpha/api/snapshots` | Save/list ratio snapshots |
| POST/GET | `/alpha/api/valuations` | Save/list valuation results |

### Export APIs
| Method | Path | Purpose |
|--------|------|---------|
| POST | `/alpha/api/export/csv` | Download CSV |
| POST | `/alpha/api/export/json` | Download JSON |
| POST | `/alpha/api/export/pdf` | Download PDF report |

---

## Frontend (SPA with Hash Routing)

**Tech:** Vanilla JS + Plotly.js (same stack as existing app, no build tools)

**Pages (hash routes):**
| Route | Page | Key Features |
|-------|------|-------------|
| `#dashboard` | Dashboard | Watchlist overview, recent notes, quick-add ticker |
| `#detail/<ticker>` | Detail | Summary, financials, ratios, trends, anomaly alerts, charts |
| `#compare` | Comparison | Multi-ticker input, comparison tables, radar/bar charts |
| `#model/<ticker>` | Modelling | DCF form, scenario editor, sensitivity heatmap |
| `#notes` | Notes | All notes, filter by ticker/tag, CRUD |
| `#watchlists` | Watchlists | Manage watchlists + tickers |

---

## Key Financial Calculations

**Valuation:** PER, PBV, EV/EBITDA, PEG
**Profitability:** ROE, ROA, NPM, GPM
**Risk:** Beta, DER, Interest Coverage, Current Ratio
**Growth:** Revenue CAGR, EPS CAGR, FCF Growth
**DCF:** FCFF projection → discount at WACC → terminal value → intrinsic value per share
**Anomaly Detection:** Z-score flagging, receivables vs revenue growth, FCF vs net income divergence

---

## New Dependencies

Add to `pyproject.toml`:
- `flask-sqlalchemy>=3.1` - ORM
- `cachetools>=5.3` - TTL caching for yfinance calls
- `scipy>=1.12` - Linear regression for projections
- `fpdf2>=2.7` - PDF generation (pure Python, no system deps)

---

## Implementation Order (8 Phases)

### Phase 1: Foundation
- Create alpha/ package structure
- SQLAlchemy models + DB init
- Enhanced data_fetcher with caching
- Ratio + growth calculation modules
- SPA shell + hash router
- Register Blueprint in app.py
- **Verify:** `/alpha/` loads, existing `/` still works

### Phase 2: Financial Statements
- Financial statement parser (income, balance, cashflow)
- Auto-computed ratios + trendlines
- Detail page frontend with tables + Plotly charts
- **Verify:** `#detail/BBCA.JK` shows full financial data

### Phase 3: Comparison Engine
- Multi-ticker comparison service
- Comparison API + frontend page
- Radar charts + grouped bar charts
- **Verify:** Compare 3-4 IDX tickers side-by-side

### Phase 4: Trend Analysis + Anomaly Detection
- YoY/QoQ computation
- Anomaly detection algorithms
- Integrate into detail page
- **Verify:** Trend highlights and anomaly alerts appear

### Phase 5: Modelling Engine
- DCF, scenario, sensitivity, projection services
- Modelling page with editable forms
- Sensitivity heatmap rendering
- **Verify:** DCF produces reasonable valuation for BBCA.JK

### Phase 6: Portfolio & Watchlist
- CRUD for watchlists, notes, snapshots
- Dashboard + notes + watchlists pages
- **Verify:** Create watchlist, add tickers, save notes, persist across restart

### Phase 7: Export
- CSV + JSON export (straightforward)
- PDF report generation with fpdf2
- Export buttons across all pages
- **Verify:** Download CSV/JSON/PDF of comparison results

### Phase 8: Polish
- Error handling audit
- Loading states + empty states
- Mobile responsive pass
- Performance optimization

---

## Known Limitations

1. **yfinance provides ~4 years of financial statements** (not 10). Price history available for 10+ years. UI will clearly label data availability.
2. **Segment revenue, market share, competitive landscape** not available from yfinance. Trend analysis will use aggregate financials + price data.
3. **Some IDX (.JK) info fields missing** (PEG, forwardPE). All calculations handle None gracefully → show "N/A".
4. **Max 8 tickers** for comparison to keep response times reasonable.

---

## Verification

After full implementation:
1. `uv sync` - install new dependencies
2. `uv run stock-checker-web` - start server
3. Visit `http://127.0.0.1:5000/` - existing app still works
4. Visit `http://127.0.0.1:5000/alpha/` - new SPA loads
5. Test each hash route with IDX tickers (BBCA.JK, BBRI.JK, TLKM.JK)
6. Test via tunnel: `https://stock.zuhdi.id/alpha/`
7. Test persistence: create watchlist, add notes, restart server, verify data persists
8. Test exports: download CSV, JSON, PDF
