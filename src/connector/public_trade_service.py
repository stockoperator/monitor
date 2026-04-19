from logging import Logger
from aiohttp import ClientSession
from abc import ABC, abstractmethod
import numpy as np

from connector.async_logger import null_logger
from connector.instrument import BaseInstrumentManager
from connector.data_service import BaseDataService


class BasePublicTrades(ABC):
    __slots__ = ("size", "idx", "wrapped")

    def __init__(self, size: int = 10_000):
        self.size = size
        self.idx: int = -1
        self.wrapped: bool = False

    def __len__(self) -> int:
        return self.size if self.wrapped else self.idx + 1

    @abstractmethod
    def add(self, timestamp_ms: int, price: float, volume: float, is_buy: bool) -> None: ...


class PublicTrades(BasePublicTrades):
    __slots__ = ("timestamps", "prices", "volumes")

    def __init__(self, size: int = 10_000, period_sec: int = 60):
        super().__init__(size=size)
        self.timestamps = np.zeros(size, dtype=np.int64)
        self.prices = np.zeros(size, dtype=np.float64)
        self.volumes = np.zeros(size, dtype=np.float64)

    def add(self, timestamp_ms: int, price: float, volume: float, is_buy: bool) -> None:
        self.idx += 1
        if self.idx == self.size:
            self.idx = 0
            self.wrapped = True
        self.timestamps[self.idx] = timestamp_ms
        self.prices[self.idx] = price
        self.volumes[self.idx] = volume if is_buy else -volume


class PublicTimeFrameTrades(PublicTrades):
    __slots__ = ("period_ms", "delta_volumes")

    def __init__(self, size: int = 10_000, period_sec: int = 60):
        super().__init__(size=size)
        self.period_ms = period_sec * 1000
        self.delta_volumes = np.zeros(size, dtype=np.float64)

    def add(self, timestamp_ms: int, price: float, volume: float, is_buy: bool) -> None:
        timestamp_ms = (timestamp_ms // self.period_ms) * self.period_ms

        if self.idx == -1 or timestamp_ms > self.timestamps[self.idx]:
            self.idx += 1
            if self.idx == self.size:
                self.idx = 0
                self.wrapped = True
            self.timestamps[self.idx] = timestamp_ms
            self.volumes[self.idx] = 0.0
            self.delta_volumes[self.idx] = 0.0
        elif timestamp_ms < self.timestamps[self.idx]:  # maybe log error
            return

        self.prices[self.idx] = price
        self.volumes[self.idx] += volume
        self.delta_volumes[self.idx] += volume if is_buy else -volume

    def ordered(self) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        end = len(self)
        split_idx = self.idx + 1
        ts = np.concatenate((self.timestamps[split_idx:end], self.timestamps[:split_idx]))
        p = np.concatenate((self.prices[split_idx:end], self.prices[:split_idx]))
        v = np.concatenate((self.volumes[split_idx:end], self.volumes[:split_idx]))
        d = np.concatenate((self.delta_volumes[split_idx:end], self.delta_volumes[:split_idx]))

        return ts, p, v, d


class PublicSideTrades(BasePublicTrades):
    __slots__ = ("timestamps", "open_prices", "close_prices", "volumes")

    def __init__(self, size: int = 10_000):
        super().__init__(size=size)
        self.timestamps = np.zeros(size, dtype=np.int64)
        self.open_prices = np.zeros(size, dtype=np.float64)
        self.close_prices = np.zeros(size, dtype=np.float64)
        self.volumes = np.zeros(size, dtype=np.float64)

    def add(self, timestamp_ms: int, price: float, volume: float, is_buy: bool) -> None:
        if not is_buy:
            volume = -volume

        if self.idx == -1 or self.volumes[self.idx] * volume < 0.0:
            self.idx += 1
            if self.idx == self.size:
                self.idx = 0
                self.wrapped = True
            self.timestamps[self.idx] = timestamp_ms
            self.open_prices[self.idx] = price
            self.close_prices[self.idx] = price
            self.volumes[self.idx] = volume
        else:
            self.close_prices[self.idx] = price
            self.volumes[self.idx] += volume


class TradesContainer:
    __slots__ = ("public_trades", "public_trades_1s", "public_trades_1m", "public_trades_1h", "public_side_trades")

    def __init__(self, size: int = 1440, size_1s: int = 1440, size_1m: int = 1440, size_1h: int = 1440):
        self.public_trades = PublicTrades(size=size)
        self.public_trades_1s = PublicTimeFrameTrades(size=size_1s, period_sec=1)
        self.public_trades_1m = PublicTimeFrameTrades(size=size_1m, period_sec=60)
        self.public_trades_1h = PublicTimeFrameTrades(size=size_1h, period_sec=60 * 60)
        self.public_side_trades = PublicSideTrades()

    def add(self, timestamp_ms: int, price: float, volume: float, is_buy: bool) -> None:
        self.public_trades.add(timestamp_ms, price, volume, is_buy)
        self.public_trades_1s.add(timestamp_ms, price, volume, is_buy)
        self.public_trades_1m.add(timestamp_ms, price, volume, is_buy)
        self.public_trades_1h.add(timestamp_ms, price, volume, is_buy)
        self.public_side_trades.add(timestamp_ms, price, volume, is_buy)


class BasePublicTradeService(BaseDataService):
    def __init__(self, *, session: ClientSession, instruments: BaseInstrumentManager, logger: Logger = null_logger()) -> None:
        super().__init__(
            session=session,
            instruments=instruments,
            logger=logger,
        )
        self.containers: dict[str, TradesContainer] = {}

    def __getitem__(self, symbol: str) -> TradesContainer:
        if symbol not in self.containers:
            self.containers[symbol] = TradesContainer()
        return self.containers[symbol]
