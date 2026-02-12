import argparse
import sys

from stock_checker.fetcher import fetch_stock
from stock_checker.indicators import calc_sma, calc_rsi, get_summary, print_summary, print_technicals
from stock_checker.plotter import plot_stock


def main():
    parser = argparse.ArgumentParser(description="Stock market analysis CLI")
    parser.add_argument("tickers", nargs="+", help="Stock ticker symbol(s), e.g. ISAT.JK BBCA.JK")
    parser.add_argument("--period", default="1y", help="Data period: 1mo, 3mo, 6mo, 1y, 2y, 5y (default: 1y)")
    parser.add_argument("--output", default=None, help="Output filename for chart (default: {ticker}_chart.png)")
    parser.add_argument("--no-plot", action="store_true", help="Skip chart generation, text output only")
    args = parser.parse_args()

    for ticker in args.tickers:
        print(f"\n{'='*50}")
        print(f"  Analyzing {ticker} (period: {args.period})")
        print(f"{'='*50}")

        try:
            stock, df = fetch_stock(ticker, period=args.period)
        except ValueError as e:
            print(f"  Error: {e}", file=sys.stderr)
            continue

        # Summary
        summary = get_summary(stock)
        print_summary(summary)

        # Technical indicators
        df = calc_sma(df)
        df = calc_rsi(df)
        print_technicals(df)

        # Chart
        if not args.no_plot:
            output = args.output if len(args.tickers) == 1 else None
            plot_stock(df, ticker, output=output)


if __name__ == "__main__":
    main()
