# stock-checker

CLI stock market analysis tool. Fetches stock data, prints summary and technical indicators, and generates candlestick charts.

## Setup

```bash
uv sync
```

## Usage

```bash
# Basic — fetches 1 year of data, prints summary + technicals, saves chart
uv run stock-checker ISAT.JK

# Custom period
uv run stock-checker BBCA.JK --period 6mo

# Text only (no chart)
uv run stock-checker TLKM.JK --no-plot

# Multiple tickers
uv run stock-checker BBCA.JK TLKM.JK ISAT.JK

# Save chart to specific file
uv run stock-checker ISAT.JK --output my_chart.png
```

## Options

| Flag | Description | Default |
|---|---|---|
| `tickers` | One or more stock ticker symbols | required |
| `--period` | Data period (1mo, 3mo, 6mo, 1y, 2y, 5y) | `1y` |
| `--output` | Output filename for chart | `{ticker}_chart.png` |
| `--no-plot` | Skip chart generation, text only | `False` |

## Technical Indicators

- **SMA** — Simple Moving Averages (20, 50, 200 day)
- **RSI** — Relative Strength Index (14 day)
- **Volume trend** — Average volume analysis
