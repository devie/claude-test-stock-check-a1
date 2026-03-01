# StockAlpha

Full-stack stock market analysis platform with interactive charts, sector-aware scoring, financial modelling, AI-powered recommendations, and portfolio management.

**Live Demo:** [stock.zuhdi.id](https://stock.zuhdi.id)

## Features

### Interactive Dashboard
- Candlestick charts with Plotly (zoom, pan, hover)
- Technical indicators: SMA, EMA, RSI, MACD, Bollinger Bands, Volume
- Configurable periods: 1mo to max

### Scoring System (3-Pillar, Sector-Aware)
- **Quality** (35%) — ROE, ROA, NPM, GPM, revenue/NI/FCF CAGR
- **Valuation** (35%) — PER, PBV, EV/EBITDA, PEG (sector-weighted)
- **Risk** (30%) — DER, Beta, Current Ratio
- Composite score with Buy/Hold/Avoid recommendation
- Sector-specific weights for Banking, Tech, Consumer, Energy, Telco, Property

### Financial Analysis
- Income statement, balance sheet, cash flow (annual + quarterly)
- Profitability, valuation, and leverage ratios
- Trend analysis with CAGR calculations
- Anomaly detection (margin compression, receivable spikes, FCF misalignment)

### Financial Modelling
- **DCF** — Discounted Cash Flow with terminal value
- **Scenario Analysis** — Bull/Base/Bear with probability weights
- **Sensitivity Matrix** — WACC vs Growth rate grid
- **DDM** — Dividend Discount Model
- **PBV / ROE models** — Book value and sustainable growth

### AI-Powered Recommendations
- Multi-provider: Groq (default), Ollama (local), Anthropic (Claude), OpenAI
- Batch scoring for entire watchlists
- Narrative analysis per ticker (Indonesian/English)
- Auto-fallback between providers

### Stock Comparison
- Up to 8 tickers side-by-side
- Valuation, profitability, risk, and market metrics
- Sector-normalized comparisons

### Industry Analysis
- Auto-detects sector (Banking, Tech, FMCG, Telco, Property, etc.)
- Sector-specific metrics and valuation zones
- Peer comparison with 2 related tickers
- Sector thesis and structural drivers

### Portfolio & Watchlist
- Create/manage multiple watchlists with categories
- Analysis notes per ticker with tags
- Ratio snapshots for historical tracking
- Saved valuation results

### Company Info & News
- Company overview, officers, major shareholders
- Corporate calendar (earnings, dividends, splits)
- Multi-ticker news aggregation with summaries

### Data Export
- CSV, JSON, and PDF report generation
- Comparison tables, scores, financials exportable

### Market Indices
- Dashboard index chips: IHSG, LQ45, S&P 500, NASDAQ, Nikkei, Hang Seng, FTSE, DAX
- Click any chip to instantly load its price chart

### Recommendation Summary
- Auto-computed 3-horizon signals (short/medium/long-term)
- Based on: 52-week position, PER, NI CAGR, ROE, DER, Revenue CAGR
- BUY/HOLD/SELL with bullet-point reasoning

### Screenshot to Clipboard
- HD 2x PNG screenshot via html2canvas
- Copies directly to clipboard (falls back to download on non-HTTPS)

### Security
- Exception sanitization (no internal info leakage)
- Input validation on all parameters
- SSRF protection on external API calls

### CLI Mode
- Single or batch ticker analysis
- Static candlestick chart generation (PNG)
- Technical indicators: SMA (20/50/200), RSI, volume trend

## Tech Stack

| Layer | Technology |
|-------|------------|
| Backend | Python 3.12, Flask, Flask-SQLAlchemy |
| Data | yfinance, NumPy, SciPy |
| Charts | Plotly.js (web), mplfinance (CLI) |
| Database | SQLite |
| AI | Groq SDK, Anthropic SDK, OpenAI SDK |
| Export | fpdf2 (PDF), csv (stdlib) |
| Deploy | Gunicorn, Cloudflare Tunnel |

## Quick Start

```bash
# Install dependencies
uv sync

# Run web server (opens Alpha dashboard)
uv run stock-checker-web
```

Open [http://localhost:5000](http://localhost:5000) — redirects to `/alpha/`

### CLI Usage

```bash
# Basic analysis
uv run stock-checker BBCA.JK

# Custom period, no chart
uv run stock-checker TLKM.JK --period 6mo --no-plot

# Multiple tickers
uv run stock-checker BBCA.JK TLKM.JK ISAT.JK
```

### Environment Variables (for AI features)

```bash
# .env file
LLM_PROVIDER=groq          # groq | ollama | anthropic | openai
GROQ_API_KEY=gsk_...
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...
OLLAMA_MODEL=llama3.2:1b   # for local inference
```

## Production

```bash
gunicorn wsgi:app --bind 0.0.0.0:5000
```
