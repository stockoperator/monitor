from datetime import datetime, timezone

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter
from connector.public_trade_service import BasePublicTrades, PublicTimeFrameTrades, TradesContainer
from connector.connector import BaseConnector

PRICE_COLOR = "tab:blue"
DELTA_COLOR = "tab:red"


def _left_bound_ms(from_ts_ms: int | None = None, from_date_utc: str | None = None) -> int:
    """
    Возвращает левую границу фильтра в миллисекундах Unix epoch.
    from_date_utc интерпретируется как UTC.
    """
    if from_ts_ms is not None:
        return from_ts_ms

    if from_date_utc is None:
        return 0

    dt = datetime.fromisoformat(from_date_utc)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    else:
        dt = dt.astimezone(timezone.utc)

    return int(dt.timestamp() * 1000)


def _ring_parts(arr: np.ndarray, split_idx: int, end: int) -> tuple[np.ndarray, np.ndarray]:
    """
    Возвращает данные кольцевого буфера в хронологическом порядке как две части:
    oldest -> newest = part1, затем part2.

    Никаких копий массива не создаёт.
    """
    return arr[split_idx:end], arr[:split_idx]


def _resolve_series(trade_container: TradesContainer, feature: str) -> BasePublicTrades:
    """
    feature:
      - 'raw' | 'public_trades' -> trade_container.public_trades
      - '1s' | '1m' | '1h'      -> trade_container.public_trades_1s / 1m / 1h
    """
    if feature in ("raw", "public_trades"):
        return trade_container.public_trades

    attr = f"public_trades_{feature}"
    try:
        return getattr(trade_container, attr)
    except AttributeError as exc:
        raise ValueError(f"Неизвестный feature={feature!r}. Допустимые значения: " f"'raw', 'public_trades', '1s', '1m', '1h'.") from exc


def _trim_left(
    ts1: np.ndarray,
    p1: np.ndarray,
    d1: np.ndarray,
    ts2: np.ndarray,
    p2: np.ndarray,
    d2: np.ndarray,
    left_ms: int,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """
    Обрезает данные слева по времени без склейки частей.
    Предполагается, что ts1 и ts2 individually sorted ascending, а вся последовательность
    равна ts1 + ts2 в хронологическом порядке.
    """
    if ts1.size:
        if left_ms <= ts1[-1]:
            i1 = np.searchsorted(ts1, left_ms, side="left")
            return ts1[i1:], p1[i1:], d1[i1:], ts2, p2, d2

        # Левая граница правее первой части: отбрасываем её целиком.
        ts1, p1, d1 = ts1[:0], p1[:0], d1[:0]

    if ts2.size:
        i2 = np.searchsorted(ts2, left_ms, side="left")
        return ts1, p1, d1, ts2[i2:], p2[i2:], d2[i2:]

    return ts1, p1, d1, ts2, p2, d2


def _cum_delta_two_parts(d1: np.ndarray, d2: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """
    Считает накопленную дельту для двух частей без их склейки.
    """
    cd1 = np.cumsum(d1, dtype=np.float64) if d1.size else d1
    if d2.size:
        base = cd1[-1] if cd1.size else 0.0
        cd2 = base + np.cumsum(d2, dtype=np.float64)
    else:
        cd2 = d2
    return cd1, cd2


def _delta_axis_formatter(value: float, _pos: int) -> str:
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
    from_ts_ms: int | None = None,
    from_date_utc: str | None = None,
    figsize: tuple[int, int] = (14, 7),
) -> None:
    """
    Строит один график с двумя осями:
      - левая ось: price
      - правая ось: cumulative delta

    Для feature='1s'/'1m'/'1h' используется delta_volumes.
    Для feature='raw' используется signed volumes из PublicTrades.
    """
    trade_container = connector.trade_service[symbol]
    public_trades = _resolve_series(trade_container, feature)
    if len(public_trades) == 0:
        print(f"{symbol}: буфер пуст")
        return

    split_idx = public_trades.idx + 1
    end = len(public_trades)

    ts1, ts2 = _ring_parts(public_trades.timestamps, split_idx, end)
    p1, p2 = _ring_parts(public_trades.prices, split_idx, end)

    # Для PublicTimeFrameTrades используем delta_volumes,
    # для PublicTrades дельта = signed volumes.
    if hasattr(public_trades, "delta_volumes") and isinstance(public_trades, PublicTimeFrameTrades):
        d1, d2 = _ring_parts(public_trades.delta_volumes, split_idx, end)
    else:
        d1, d2 = _ring_parts(public_trades.volumes, split_idx, end)

    left_ms = _left_bound_ms(from_ts_ms=from_ts_ms, from_date_utc=from_date_utc)

    ts1, p1, d1, ts2, p2, d2 = _trim_left(ts1, p1, d1, ts2, p2, d2, left_ms)

    if ts1.size == 0 and ts2.size == 0:
        print(f"{symbol}: после фильтра данных нет")
        return

    cd1, cd2 = _cum_delta_two_parts(d1 * p1, d2 * p2)

    x1 = ts1.astype("datetime64[ms]")
    x2 = ts2.astype("datetime64[ms]")

    fig, ax1 = plt.subplots(figsize=figsize)  # type: ignore

    if x1.size:
        ax1.plot(x1, p1, linewidth=1.0, color=PRICE_COLOR)  # type: ignore
    if x2.size:
        ax1.plot(x2, p2, linewidth=1.0, color=PRICE_COLOR)  # type: ignore

    ax1.set_xlabel("time")  # type: ignore
    ax1.set_ylabel("price, usd", color=PRICE_COLOR)  # type: ignore
    ax1.tick_params(axis="y", labelcolor=PRICE_COLOR)  # type: ignore
    ax1.grid(True, linestyle="--", alpha=0.5)  # type: ignore

    last_price = round(p2[-1] if p2.size else p1[-1], 10)
    ax1.axhline(last_price, linestyle="--", alpha=0.35, color=PRICE_COLOR)  # type: ignore

    ax2 = ax1.twinx()

    if x1.size:
        ax2.plot(x1, cd1, linewidth=1.0, color=DELTA_COLOR)  # type: ignore
    if x2.size:
        ax2.plot(x2, cd2, linewidth=1.0, color=DELTA_COLOR)  # type: ignore

    ax2.set_ylabel("cumulative delta, usd", color=DELTA_COLOR)  # type: ignore
    ax2.tick_params(axis="y", labelcolor=DELTA_COLOR)  # type: ignore
    ax2.yaxis.set_major_formatter(FuncFormatter(_delta_axis_formatter))

    last_cd = round(cd2[-1] if p2.size else cd1[-1], 10)
    ax2.axhline(last_cd, linestyle="--", alpha=0.35, color=DELTA_COLOR)  # type: ignore

    start_x = x1[0] if x1.size else x2[0]
    end_x = x2[-1] if x2.size else x1[-1]
    start_str = np.datetime_as_string(start_x, unit="s").replace("T", " ")  # type: ignore
    end_str = np.datetime_as_string(end_x, unit="s").replace("T", " ")  # type: ignore

    connector_name = connector.__class__.__name__
    points_count = x1.size + x2.size
    ax1.set_title(f"{connector_name} | {symbol} | tf: {feature} | {start_str} - {end_str} | points: {points_count} | price: {last_price}")  # type: ignore

    fig.autofmt_xdate()
    fig.tight_layout()
    plt.show()  # type: ignore
