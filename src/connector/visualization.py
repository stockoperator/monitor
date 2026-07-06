import numpy as np
import matplotlib.pyplot as plt
from matplotlib.ticker import AutoMinorLocator
from matplotlib.ticker import FuncFormatter

from connector.kline_service import Klines, KlinesContainer
from connector.connector import BaseConnector

plt.rcParams["font.sans-serif"] = ["Noto Sans CJK SC", "WenQuanYi Zen Hei"]
plt.rcParams["axes.unicode_minus"] = False  # чтобы минус нормально показывался


PRICE_COLOR = "tab:blue"
NOTIONAL_COLOR = "tab:blue"
NOTIONAL_DELTA_COLOR = "tab:red"
IMPACT_COLOR = "tab:blue"


def _axis_formatter(value: float, _pos: int) -> str:
    abs_value = abs(value)

    if abs_value >= 1_000_000:
        return f"{value / 1_000_000:.1f}M"

    if abs_value >= 1_000:
        return f"{value / 1_000:.0f}K"

    return f"{round(value, 8)}"


def plot_price_and_cumulative_delta_notional(
    symbol: str,
    connector: BaseConnector,
    feature: str = "1s",
    from_date_utc: str | None = None,
    to_date_utc: str | None = None,
    figsize: tuple[int, int] = (14, 7),
) -> None:
    """
    Строит график с несколькими панелями:

      1. price + cumulative delta notional + volume + cumulative delta volume
      2. notional volume
      3. volume ratio
      4. price impact per directed delta

    Где:
      - dn -> cumulative delta notional, usd
      - dv -> cumulative delta volume
    """

    trade_container: KlinesContainer = connector.kline_service[symbol]
    klines: Klines = getattr(trade_container, f"klines_{feature}")
    connector_name = connector.__class__.__name__

    ts, p, n, dn = klines.ordered(from_date_utc, to_date_utc)

    if not ts.size > 1:
        print(f"{connector_name} {symbol}: Данных нет")
        return

    cd = np.cumsum(dn, dtype=np.float64)

    x = ts.astype("datetime64[ms]")

    last_price = round(p[-1], 10)
    last_cd = round(cd[-1], 10)

    fig, (ax_price, ax_nv, ax_ratio, ax_impact) = plt.subplots(4, 1, figsize=figsize, sharex=True, gridspec_kw={"height_ratios": (3, 1, 1, 1)})  # type: ignore

    # -----------------------------
    # График 1: price
    # -----------------------------
    ax_price.plot(x, p, linewidth=1.0, color=PRICE_COLOR, label="price")  # type: ignore

    ax_price.set_ylabel("price, usd")  # type: ignore
    ax_price.tick_params(axis="y", labelcolor=PRICE_COLOR)  # type: ignore

    ax_price.axhline(last_price, linestyle="--", alpha=0.35, color=PRICE_COLOR)  # type: ignore

    ax_price.xaxis.set_minor_locator(AutoMinorLocator())

    ax_price.grid(True, which="major", linestyle="-", linewidth=1, alpha=0.7)

    ax_price.grid(True, which="minor", linestyle="--", linewidth=0.7, alpha=0.7)

    # -----------------------------
    # График 1: cumulative delta notional
    # -----------------------------
    ax_cnd = ax_price.twinx()

    ax_cnd.plot(x, cd, linewidth=1.0, color=NOTIONAL_DELTA_COLOR, label="cumulative delta, usd")  # type: ignore

    ax_cnd.set_ylabel("cumulative delta, usd", color=NOTIONAL_DELTA_COLOR)  # type: ignore
    ax_cnd.tick_params(axis="y", labelcolor=NOTIONAL_DELTA_COLOR)  # type: ignore
    ax_cnd.yaxis.set_major_formatter(FuncFormatter(_axis_formatter))

    ax_cnd.axhline(last_cd, linestyle="--", alpha=0.35, color=NOTIONAL_DELTA_COLOR)  # type: ignore

    # -----------------------------
    # График 2: notional volume
    # -----------------------------
    ax_nv.fill_between(x, n, 0.0, step="mid", color=NOTIONAL_COLOR, linewidth=0.0)  # type: ignore

    ax_nv.set_ylabel("volume, usd")  # type: ignore
    ax_nv.yaxis.set_major_formatter(FuncFormatter(_axis_formatter))

    ax_nv.xaxis.set_minor_locator(AutoMinorLocator())

    ax_nv.grid(True, which="major", linestyle="-", linewidth=1, alpha=0.7)

    ax_nv.grid(True, which="minor", linestyle="--", linewidth=0.7, alpha=0.7)

    # -----------------------------
    # График 3: volume ratio
    # -----------------------------
    volume_ratio = 100 * (1 + dn / np.where(n == 0, 1e-10, n)) / 2

    ax_ratio.plot(x, volume_ratio, linewidth=1.0, color=IMPACT_COLOR)  # type: ignore

    ax_ratio.set_ylabel("volume ratio")  # type: ignore
    ax_ratio.set_xlabel("time")  # type: ignore
    ax_ratio.yaxis.set_major_formatter(FuncFormatter(_axis_formatter))

    ax_ratio.axhline(50, linestyle="--", alpha=0.35, color=IMPACT_COLOR)  # type: ignore

    ax_ratio.xaxis.set_minor_locator(AutoMinorLocator())

    ax_ratio.grid(True, which="major", linestyle="-", linewidth=1, alpha=0.7)

    ax_ratio.grid(True, which="minor", linestyle="--", linewidth=0.7, alpha=0.7)

    # -----------------------------
    # График 4: price impact per directed delta
    # rolling window 30
    # фильтр: учитываем только свечи, где volume > 10_000$
    # -----------------------------

    # close-to-close изменение цены
    price_ret = np.full_like(p, np.nan, dtype=np.float64)
    price_ret[1:] = p[1:] / np.where(p[:-1] == 0, np.nan, p[:-1]) - 1.0

    impact_window = 30

    # фильтр по общему объёму свечи
    min_volume_usd = 10_000.0
    volume_mask = n > min_volume_usd

    # фильтр по направленной дельте
    min_abs_delta = 0.0

    buyer_mask = (dn > min_abs_delta) & volume_mask & np.isfinite(price_ret)

    seller_mask = (dn < -min_abs_delta) & volume_mask & np.isfinite(price_ret)

    # numerator / denominator отдельно,
    # чтобы не усреднять ratio неправильно
    buyer_num = np.where(buyer_mask, price_ret, 0.0)
    buyer_den = np.where(buyer_mask, dn / 1_000_000.0, 0.0)

    seller_num = np.where(seller_mask, -price_ret, 0.0)
    seller_den = np.where(seller_mask, (-dn) / 1_000_000.0, 0.0)

    def _rolling_sum_trailing(a: np.ndarray, window: int) -> np.ndarray:
        """
        Trailing rolling sum:

            result[i] = sum(a[i-window+1 : i+1])

        Без подглядывания в будущее.
        """
        if window <= 1:
            return a.astype(np.float64)

        a = a.astype(np.float64)

        c = np.cumsum(np.r_[0.0, a])
        out = c[window:] - c[:-window]

        # первые window - 1 значений считаем по доступной истории
        head = c[1:window] - c[0]

        return np.r_[head, out]

    buyer_num_rolling = _rolling_sum_trailing(buyer_num, impact_window)
    buyer_den_rolling = _rolling_sum_trailing(buyer_den, impact_window)

    seller_num_rolling = _rolling_sum_trailing(seller_num, impact_window)
    seller_den_rolling = _rolling_sum_trailing(seller_den, impact_window)

    buyer_impact = np.divide(
        100.0 * buyer_num_rolling,
        buyer_den_rolling,
        out=np.full_like(buyer_num_rolling, np.nan, dtype=np.float64),
        where=buyer_den_rolling > 0,
    )

    seller_impact = np.divide(
        100.0 * seller_num_rolling,
        seller_den_rolling,
        out=np.full_like(seller_num_rolling, np.nan, dtype=np.float64),
        where=seller_den_rolling > 0,
    )

    ax_impact.plot(x, buyer_impact, linewidth=1.0, color="g", label="buyer impact")

    ax_impact.plot(x, seller_impact, linewidth=1.0, color="r", label="seller impact")

    ax_impact.set_ylabel("impact 30\n% / 1M delta")
    ax_impact.set_xlabel("time")
    ax_impact.axhline(0, linestyle="--", alpha=0.35)

    ax_impact.yaxis.set_major_formatter(FuncFormatter(_axis_formatter))
    ax_impact.xaxis.set_minor_locator(AutoMinorLocator())

    ax_impact.grid(True, which="major", linestyle="-", linewidth=1, alpha=0.7)

    ax_impact.grid(True, which="minor", linestyle="--", linewidth=0.7, alpha=0.7)

    ax_impact.legend(loc="upper left", fontsize=8, framealpha=0.85)

    # -----------------------------
    # Общие подписи
    # -----------------------------
    start_x = x[0]
    end_x = x[-1]

    start_str = np.datetime_as_string(start_x, unit="s").replace("T", " ")  # type: ignore
    end_str = np.datetime_as_string(end_x, unit="s").replace("T", " ")  # type: ignore

    points_count = x.size

    fr = ""
    if connector.funding_service:
        funding_rate = connector.funding_service[symbol]
        if funding_rate and funding_rate.rate:
            fr = f" | fr: {funding_rate.rate * 100:.1f}%"

    ax_price.set_title(
        (f"{connector_name} | {symbol} | tf: {feature} | " f"{start_str} - {end_str} | points: {points_count} | " f"price: {last_price}{fr}")
    )  # type: ignore

    fig.autofmt_xdate()

    # rect нужен, чтобы третья правая ось не обрезалась
    fig.tight_layout(rect=(0, 0, 0.88, 1))

    plt.show()  # type: ignore
