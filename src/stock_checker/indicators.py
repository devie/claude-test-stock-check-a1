import numpy as np


def calc_sma(df, windows=(20, 50, 200)):
    """Add SMA columns to DataFrame."""
    for w in windows:
        df[f"SMA_{w}"] = df["Close"].rolling(window=w).mean()
    return df


def calc_rsi(df, period=14):
    """Add RSI column to DataFrame."""
    delta = df["Close"].diff()
    gain = delta.where(delta > 0, 0.0)
    loss = -delta.where(delta < 0, 0.0)

    avg_gain = gain.rolling(window=period, min_periods=period).mean()
    avg_loss = loss.rolling(window=period, min_periods=period).mean()

    rs = avg_gain / avg_loss
    df["RSI"] = 100 - (100 / (1 + rs))
    return df


def get_summary(ticker_obj):
    """Extract summary info from a yfinance Ticker object."""
    info = ticker_obj.info
    return {
        "Name": info.get("longName") or info.get("shortName", "N/A"),
        "Sector": info.get("sector", "N/A"),
        "Market Cap": info.get("marketCap"),
        "Current Price": info.get("currentPrice") or info.get("regularMarketPrice"),
        "52W High": info.get("fiftyTwoWeekHigh"),
        "52W Low": info.get("fiftyTwoWeekLow"),
        "Avg Volume": info.get("averageVolume"),
    }


def format_number(n):
    """Format large numbers with B/M/K suffix."""
    if n is None:
        return "N/A"
    if n >= 1_000_000_000_000:
        return f"{n / 1_000_000_000_000:.2f}T"
    if n >= 1_000_000_000:
        return f"{n / 1_000_000_000:.2f}B"
    if n >= 1_000_000:
        return f"{n / 1_000_000:.2f}M"
    if n >= 1_000:
        return f"{n / 1_000:.2f}K"
    return f"{n:.2f}"


def print_summary(summary):
    """Print stock summary to console."""
    print("\n=== Stock Summary ===")
    print(f"  Name:          {summary['Name']}")
    print(f"  Sector:        {summary['Sector']}")
    print(f"  Market Cap:    {format_number(summary['Market Cap'])}")
    print(f"  Current Price: {format_number(summary['Current Price'])}")
    print(f"  52W High:      {format_number(summary['52W High'])}")
    print(f"  52W Low:       {format_number(summary['52W Low'])}")
    print(f"  Avg Volume:    {format_number(summary['Avg Volume'])}")


def print_technicals(df):
    """Print latest technical indicator values."""
    latest = df.iloc[-1]
    print("\n=== Technical Indicators ===")

    for w in (20, 50, 200):
        col = f"SMA_{w}"
        if col in df.columns:
            val = latest[col]
            print(f"  SMA {w}:  {val:.2f}" if not np.isnan(val) else f"  SMA {w}:  N/A (not enough data)")

    if "RSI" in df.columns:
        rsi = latest["RSI"]
        if not np.isnan(rsi):
            label = "Overbought" if rsi > 70 else "Oversold" if rsi < 30 else "Neutral"
            print(f"  RSI 14:  {rsi:.2f} ({label})")
        else:
            print("  RSI 14:  N/A (not enough data)")

    # Volume trend: compare last 20-day avg vs overall avg
    if len(df) >= 20:
        recent_vol = df["Volume"].tail(20).mean()
        overall_vol = df["Volume"].mean()
        ratio = recent_vol / overall_vol if overall_vol > 0 else 0
        trend = "Above average" if ratio > 1.1 else "Below average" if ratio < 0.9 else "Average"
        print(f"  Volume:  {trend} (recent/overall = {ratio:.2f}x)")
