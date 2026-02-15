# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

Stock Checker — a CLI + web app for stock market analysis. Fetches data via yfinance, computes technical indicators (SMA, RSI, volume trend), and renders candlestick charts.

## Commands

```bash
# Install dependencies
uv sync

# Run CLI
uv run stock-checker BBCA.JK
uv run stock-checker BBCA.JK --period 6mo --no-plot
uv run stock-checker BBCA.JK TLKM.JK ISAT.JK

# Run web server (Flask dev server on :5000)
uv run stock-checker-web

# Production (gunicorn)
gunicorn wsgi:app --bind 0.0.0.0:$PORT
```

No test suite exists yet.

## Architecture

Python 3.12, managed with `uv`. Source lives in `src/stock_checker/` with hatchling as the build backend.

**Two entry points** defined in `pyproject.toml [project.scripts]`:
- `stock-checker` → `cli.py:main` — argparse CLI that analyzes one or more tickers sequentially
- `stock-checker-web` → `app.py:run` — Flask web UI with a single-page frontend

**Core modules** (`src/stock_checker/`):
- `fetcher.py` — wraps `yfinance.Ticker` to fetch history; returns `(Ticker, DataFrame)`
- `indicators.py` — computes SMA/RSI columns on the DataFrame, extracts summary from Ticker.info with fast_info fallback, formats numbers
- `plotter.py` — generates static PNG candlestick charts via mplfinance (CLI only, saves to `output/`)
- `app.py` — Flask app with `/api/analyze` POST endpoint; builds Plotly JSON (not mplfinance) for interactive browser charts
- `templates/index.html` — single-file SPA, fetches `/api/analyze` and renders with Plotly.js

**Key difference**: CLI uses mplfinance for static PNGs; web app builds Plotly-compatible JSON server-side and renders client-side.

## Deployment

- `wsgi.py` — WSGI entry point (adds `src/` to sys.path, imports `app`)
- `render.yaml` — Render.com config (gunicorn, Python 3.12, free tier)
- `deploy_pythonanywhere.sh` + `pythonanywhere_wsgi.py` — PythonAnywhere deployment
- `requirements.txt` — pip-format lockfile generated from pyproject.toml
