from logging import Logger
from aiohttp import ClientSession
from abc import ABC, abstractmethod
import numpy as np

from connector.async_logger import null_logger
from connector.instrument import BaseInstrumentManager
from connector.data_service import BaseDataService


class BasePublicTrades(ABC):
    __slots__ = ("size", "idx", "timestamps", "prices", "volumes")

    def __init__(self, size: int = 10_000):
        self.size = size
        self.idx: int = -1
        self.timestamps = np.zeros(size, dtype=np.int64)
        self.prices = np.zeros(size, dtype=np.float64)
        self.volumes = np.zeros(size, dtype=np.float64)

    def __len__(self) -> int:
        return min(self.idx + 1, self.size)

    @abstractmethod
    def add(self, timestamp_ms: int, price: float, amount: float, is_buy: bool) -> None: ...


class PublicTrades(BasePublicTrades):
    def add(self, timestamp_ms: int, price: float, amount: float, is_buy: bool) -> None:
        self.idx += 1
        i = self.idx % self.size
        self.timestamps[i] = timestamp_ms
        self.prices[i] = price
        self.volumes[i] = amount if is_buy else -amount

    @property
    def last_price(self) -> float:
        return float(self.prices[self.idx % self.size])


class PublicTimeFrameTrades(BasePublicTrades):
    __slots__ = BasePublicTrades.__slots__ + ("period_ms", "delta_volumes")

    def __init__(self, size: int = 10_000, period_sec: int = 60):
        super().__init__(size=size)
        self.period_ms = period_sec * 1000
        self.delta_volumes = np.zeros(size, dtype=np.float64)

    def add(self, timestamp_ms: int, price: float, amount: float, is_buy: bool) -> None:
        timestamp_ms = (timestamp_ms // self.period_ms) * self.period_ms
        i = self.idx % self.size

        if i == -1 or timestamp_ms > self.timestamps[i]:
            self.idx += 1
            i = self.idx % self.size
            self.timestamps[i] = timestamp_ms
            self.volumes[i] = 0.0
            self.delta_volumes[i] = 0.0
        elif timestamp_ms < self.timestamps[i]:  # maybe log error
            return

        self.prices[i] = price
        self.volumes[i] += amount
        self.delta_volumes[i] += amount if is_buy else -amount


class TradesContainer:
    def __init__(self, size: int = 1440, size_1s: int = 1440, size_1m: int = 1440, size_1h: int = 1440):
        self.public_trades = PublicTrades(size=size)
        self.public_trades_1s = PublicTimeFrameTrades(size=size_1s, period_sec=1)
        self.public_trades_1m = PublicTimeFrameTrades(size=size_1m, period_sec=60)
        self.public_trades_1h = PublicTimeFrameTrades(size=size_1h, period_sec=60 * 60)

    def add(self, timestamp_ms: int, price: float, amount: float, is_buy: bool) -> None:
        self.public_trades.add(timestamp_ms, price, amount, is_buy)
        self.public_trades_1s.add(timestamp_ms, price, amount, is_buy)
        self.public_trades_1m.add(timestamp_ms, price, amount, is_buy)
        self.public_trades_1h.add(timestamp_ms, price, amount, is_buy)


class BasePublicTradeService(BaseDataService):
    def __init__(self, *, session: ClientSession, instruments: BaseInstrumentManager, logger: Logger = null_logger()) -> None:
        super().__init__(
            session=session,
            instruments=instruments,
            logger=logger,
        )
        self._items: dict[str, TradesContainer] = {}

    def __getitem__(self, symbol: str) -> TradesContainer:
        if symbol not in self._items:
            self._items[symbol] = TradesContainer()
        return self._items[symbol]
