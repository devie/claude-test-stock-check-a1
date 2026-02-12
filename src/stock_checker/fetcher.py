import yfinance as yf


def fetch_stock(ticker, period="1y"):
    """Fetch stock data. Returns (yfinance.Ticker, DataFrame of history)."""
    stock = yf.Ticker(ticker)
    hist = stock.history(period=period)
    if hist.empty:
        raise ValueError(f"No data found for ticker '{ticker}'")
    return stock, hist
