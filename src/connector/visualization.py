from datetime import datetime, timezone

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter
from connector.kline_service import Klines, KlinesContainer
from connector.connector import BaseConnector

plt.rcParams["font.sans-serif"] = ["Noto Sans CJK SC", "WenQuanYi Zen Hei"]
plt.rcParams["axes.unicode_minus"] = False  # чтобы минус нормально показывался

PRICE_COLOR = "tab:blue"
DELTA_COLOR = "tab:red"
VOLUME_COLOR = "tab:blue"


def _axis_formatter(value: float, _pos: int) -> str:
    abs_value = abs(value)
    if abs_value >= 1_000_000:
        return f"{value / 1_000_000:.1f}M"
    if abs_value >= 1_000:
        return f"{value / 1_000:.0f}K"
    return f"{value:.0f}"


def plot_price_and_cumulative_delta_notional(
    symbol: str,
    connector: BaseConnector,
    feature: str = "1s",
    from_date_utc: str | None = None,
    figsize: tuple[int, int] = (14, 7),
) -> None:
    """
    Строит один график с двумя осями:
      - левая ось: price
      - правая ось: cumulative delta

    Для feature='1s'/'1m'/'1h' используется delta_volumes.
    """

    trade_container: KlinesContainer = connector.kline_service[symbol]
    klines: Klines = getattr(trade_container, f"klines_{feature}")
    connector_name = connector.__class__.__name__

    if len(klines) == 0:
        print(f"{connector_name} {symbol}: буфер пуст")
        return

    left_ms = int(datetime.fromisoformat(from_date_utc).replace(tzinfo=timezone.utc).timestamp() * 1000) if from_date_utc else 0

    ts, p, v, d = klines.ordered()

    i = np.searchsorted(ts, left_ms, side="left")
    ts, p, v, d = ts[i:], p[i:], v[i:], d[i:]

    if ts.size == 0:
        print(f"{connector_name} {symbol}: после фильтра данных нет")
        return

    cd = np.cumsum(d, dtype=np.float64)

    x = ts.astype("datetime64[ms]")

    fig, (ax1, ax3) = plt.subplots(2, 1, figsize=figsize, sharex=True, gridspec_kw={"height_ratios": (3, 1)})  # type: ignore

    ax1.plot(x, p, linewidth=1.0, color=PRICE_COLOR)  # type: ignore

    ax1.set_xlabel("time")  # type: ignore
    ax1.set_ylabel("price, usd", color=PRICE_COLOR)  # type: ignore
    ax1.tick_params(axis="y", labelcolor=PRICE_COLOR)  # type: ignore
    ax1.grid(True, linestyle="--", alpha=0.5)  # type: ignore

    last_price = round(p[-1], 10)
    ax1.axhline(last_price, linestyle="--", alpha=0.35, color=PRICE_COLOR)  # type: ignore

    ax2 = ax1.twinx()

    ax2.plot(x, cd, linewidth=1.0, color=DELTA_COLOR)  # type: ignore

    ax2.set_ylabel("cumulative delta, usd", color=DELTA_COLOR)  # type: ignore
    ax2.tick_params(axis="y", labelcolor=DELTA_COLOR)  # type: ignore
    ax2.yaxis.set_major_formatter(FuncFormatter(_axis_formatter))

    last_cd = round(cd[-1], 10)
    ax2.axhline(last_cd, linestyle="--", alpha=0.35, color=DELTA_COLOR)  # type: ignore

    # -----------------------------
    # Нижний график: volume
    # -----------------------------
    if ts.size > 1:
        step_ms = int(np.median(np.diff(ts)))
    else:
        step_ms = 1000

    bar_width = np.timedelta64(max(1, int(step_ms * 0.8)), "ms")

    if len(x) > 1:
        ax3.fill_between(x, v, 0.0, step="mid", color=VOLUME_COLOR, linewidth=0.0)  # type: ignore
    else:
        ax3.bar(x, v, width=bar_width, color=VOLUME_COLOR, linewidth=0.0, align="center")  # type: ignore
    ax3.set_ylabel("volume, usd")  # type: ignore
    ax3.set_xlabel(f"time {step_ms}")  # type: ignore
    ax3.grid(True, linestyle="--", alpha=0.5)  # type: ignore
    ax3.yaxis.set_major_formatter(FuncFormatter(_axis_formatter))

    # -----------------------------
    # Общие подписи
    # -----------------------------
    start_x = x[0]
    end_x = x[-1]
    start_str = np.datetime_as_string(start_x, unit="s").replace("T", " ")  # type: ignore
    end_str = np.datetime_as_string(end_x, unit="s").replace("T", " ")  # type: ignore

    points_count = x.size
    ax1.set_title(f"{connector_name} | {symbol} | tf: {feature} | {start_str} - {end_str} | points: {points_count} | price: {last_price}")  # type: ignore

    fig.autofmt_xdate()
    fig.tight_layout()
    plt.show()  # type: ignore
