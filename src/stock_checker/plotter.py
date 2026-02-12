import mplfinance as mpf
import matplotlib.pyplot as plt


def plot_stock(df, ticker, output=None):
    """Generate candlestick chart with SMA overlays, volume, and RSI subplot."""
    # Build SMA overlay plots
    add_plots = []
    colors = {"SMA_20": "blue", "SMA_50": "orange", "SMA_200": "red"}
    for col, color in colors.items():
        if col in df.columns:
            add_plots.append(mpf.make_addplot(df[col], color=color, width=0.8, label=col))

    # RSI subplot
    if "RSI" in df.columns:
        add_plots.append(mpf.make_addplot(df["RSI"], panel=2, color="purple", ylabel="RSI", width=0.8))
        # Overbought/oversold lines
        rsi_70 = [70] * len(df)
        rsi_30 = [30] * len(df)
        add_plots.append(mpf.make_addplot(rsi_70, panel=2, color="gray", linestyle="--", width=0.5))
        add_plots.append(mpf.make_addplot(rsi_30, panel=2, color="gray", linestyle="--", width=0.5))

    save_path = output or f"{ticker}_chart.png"

    fig, axes = mpf.plot(
        df,
        type="candle",
        style="charles",
        title=f"\n{ticker} Stock Chart",
        volume=True,
        addplot=add_plots if add_plots else None,
        figsize=(14, 10),
        panel_ratios=(4, 1, 2) if "RSI" in df.columns else (4, 1),
        returnfig=True,
    )

    # Add SMA legend to price panel
    sma_labels = [col for col in colors if col in df.columns]
    if sma_labels:
        sma_colors = [colors[col] for col in sma_labels]
        axes[0].legend(
            [plt.Line2D([0], [0], color=c) for c in sma_colors],
            sma_labels,
            loc="upper left",
            fontsize=8,
        )

    fig.savefig(save_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"\nChart saved to {save_path}")
