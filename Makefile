.PHONY: dev lint test run run-screen fetch-uma help

# ── Setup ─────────────────────────────────────────────────────────────────────
dev:
	uv sync
	cp -n .env.example .env 2>/dev/null || true
	mkdir -p data/alerts data/parquet

# ── Quality ───────────────────────────────────────────────────────────────────
lint:
	uv run python -m py_compile src/stock_checker/idx_anomaly/config.py
	uv run python -m py_compile src/stock_checker/idx_anomaly/features/indicators.py
	uv run python -m py_compile src/stock_checker/idx_anomaly/features/rules.py
	uv run python -m py_compile src/stock_checker/idx_anomaly/features/scoring.py
	@echo "Lint OK (no syntax errors)"

test:
	uv run pytest tests/idx_anomaly/ -v --tb=short

test-cov:
	uv run pytest tests/idx_anomaly/ -v --tb=short --cov=src/stock_checker/idx_anomaly --cov-report=term-missing

# ── Web server ────────────────────────────────────────────────────────────────
run:
	uv run stock-checker-web

# ── CLI shortcuts ─────────────────────────────────────────────────────────────
fetch-uma:
	uv run python -m stock_checker.idx_anomaly.cli fetch:uma

run-screen:
	uv run python -m stock_checker.idx_anomaly.cli run:screen \
		BBCA.JK TLKM.JK BREN.JK GOTO.JK BMRI.JK ASII.JK UNVR.JK

# ── Help ──────────────────────────────────────────────────────────────────────
help:
	@echo "make dev          Install deps + init directories"
	@echo "make lint         Syntax-check core modules"
	@echo "make test         Run pytest suite"
	@echo "make test-cov     Run pytest with coverage"
	@echo "make run          Start Flask dev server"
	@echo "make fetch-uma    Scrape IDX UMA list"
	@echo "make run-screen   Screen a default IDX watchlist"
