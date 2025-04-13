import matplotlib
matplotlib.use('Agg')  # Set non-interactive backend before importing pyplot
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import numpy as np
import io

colors = ['green', 'red', 'orange', 'purple', 'brown', 'black']

def create_price_chart(df, ticker, cols):
    lines = []
    labels = []
    fig, ax = plt.subplots(figsize=(12, 6))
    fig.suptitle(f"{ticker} Stock Price", fontsize=16)

    def plot_col(col, color):
        dates = df[df[col].notna()].index
        vals = df.loc[dates, col]
        nax = ax.twinx()
        line, = nax.plot(dates, vals, color=color, marker='o', markersize=3, linewidth=1.5)
        lines.append(line)
        labels.append(col)
        nax.yaxis.set_visible(False)

        
    line, = ax.plot(df.index, df['close'], label='Stock Price', linewidth=1.5)
    lines.append(line)
    labels.append('Stock Price')
    ax.set_title('Stock Price')
    ax.set_ylabel('Price')
    ax.grid(True) 

    ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
    ax.xaxis.set_major_locator(mdates.MonthLocator(interval=3))

    for i, c in enumerate(cols):
        plot_col(c, colors[i])

    fig.legend(lines, labels, loc="upper left", frameon=True)

    plt.xticks(rotation=45)
    plt.setp(ax.xaxis.get_majorticklabels(), rotation=45)
    plt.tight_layout()
    plt.subplots_adjust(top=0.9)

    buffer = io.BytesIO()
    plt.savefig(buffer, format='png', dpi=150, bbox_inches='tight')
    plt.close(fig)

    buffer.seek(0)

    return buffer.getvalue()

def create_line_chart(df, ticker, cols):
    n_plots = len(cols)
    fig, axes = plt.subplots(n_plots, 1, figsize=(12, 3*n_plots), sharex=True)

    if n_plots == 1:
        axes = [axes]

    fig.suptitle(f"{ticker} Financial Data", fontsize=16)

    axes[0].plot(df.index, df['close'], label='Stock Price', linewidth=1.5)
    axes[0].set_title('Stock Price')
    axes[0].set_ylabel('Price')
    axes[0].grid(True)

    axes[-1].xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
    axes[-1].xaxis.set_major_locator(mdates.MonthLocator(interval=3))


    for i, metric in enumerate(cols):
        fin_dates = df[df[metric].notna()].index
        fin_values = df.loc[fin_dates, metric]

        axes[i].plot(fin_dates, fin_values, 'g-o') #markersize=3, linewidth=2
        axes[i].set_title(metric)
        axes[i].set_ylabel('Value ($)')
        axes[i].grid(True)

    for date in df[df[cols[0]].notna()].index:
        for ax in axes:
            ax.axvline(x=date, color='gray', linestyle='--', linewidth=0.4)

    plt.tight_layout()
    plt.subplots_adjust(top=0.9)
    plt.setp(axes[-1].xaxis.get_majorticklabels(), rotation=45)
    fig.savefig('financial_chart.png', dpi=300, bbox_inches='tight')
    print("Chart saved to financial_chart.png")

    return fig

        

