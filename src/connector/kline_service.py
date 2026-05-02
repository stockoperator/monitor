from logging import Logger
from aiohttp import ClientSession
import numpy as np
from abc import abstractmethod

from connector.async_logger import null_logger
from connector.rate_limiter import BaseRateLimiterHttpClient
from connector.instrument import BaseInstrumentManager
from connector.data_service import BaseDataService


class Klines:
    __slots__ = (
        "size",
        "idx",
        "wrapped",
        "period_ms",
        "timestamps",
        "prices",
        "notionals",
        "delta_notionals",
        "closed_notional",
        "closed_delta_notional",
        "last_timestamp",
    )

    def __init__(self, size: int = 1440, period_sec: int = 60) -> None:
        self.size = size
        self.idx: int = -1
        self.wrapped: bool = False
        self.period_ms = period_sec * 1000
        self.timestamps = np.zeros(size, dtype=np.int64)
        self.prices = np.zeros(size, dtype=np.float64)
        self.notionals = np.zeros(size, dtype=np.float64)
        self.delta_notionals = np.zeros(size, dtype=np.float64)
        self.closed_notional: float = 0
        self.closed_delta_notional: float = 0
        self.last_timestamp: int = 0

    def __len__(self) -> int:
        return self.size if self.wrapped else self.idx + 1

    def set(self, timestamp: int, close: float, notional: float, delta_notional: float) -> None:
        m1 = 60_000
        open_time_1m = (timestamp // m1) * m1

        if self.idx > -1 and open_time_1m > (self.last_timestamp // m1) * m1:
            self.closed_notional = float(self.notionals[self.idx])
            self.closed_delta_notional = float(self.delta_notionals[self.idx])
        self.last_timestamp = timestamp

        open_time = (timestamp // self.period_ms) * self.period_ms

        if self.idx == -1 or open_time > self.timestamps[self.idx]:
            self.idx += 1
            if self.idx == self.size:
                self.idx = 0
                self.wrapped = True
            self.timestamps[self.idx] = open_time
            self.closed_notional = 0.0
            self.closed_delta_notional = 0.0
        elif open_time < self.timestamps[self.idx]:
            return

        self.prices[self.idx] = close
        self.notionals[self.idx] = notional + self.closed_notional
        self.delta_notionals[self.idx] = delta_notional + self.closed_delta_notional

    def ordered(self) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        end = len(self)
        split_idx = self.idx + 1
        ts = np.concatenate((self.timestamps[split_idx:end], self.timestamps[:split_idx]))
        p = np.concatenate((self.prices[split_idx:end], self.prices[:split_idx]))
        v = np.concatenate((self.notionals[split_idx:end], self.notionals[:split_idx]))
        d = np.concatenate((self.delta_notionals[split_idx:end], self.delta_notionals[:split_idx]))

        return ts, p, v, d


class KlinesContainer:
    __slots__ = ("klines_1m", "klines_1h", "klines_1d")

    def __init__(self, size_1m: int = 1440, size_1h: int = 1440, size_1d: int = 1440) -> None:
        self.klines_1m = Klines(size=size_1m, period_sec=60)
        self.klines_1h = Klines(size=size_1h, period_sec=60 * 60)
        self.klines_1d = Klines(size=size_1d, period_sec=60 * 60 * 24)

    def set(self, timestamp: int, close: float, notional: float, delta_notional: float) -> None:
        for slot in self.__slots__:
            klines: Klines = getattr(self, slot)
            klines.set(timestamp, close, notional, delta_notional)


class BaseKlineService(BaseDataService):
    def __init__(
        self,
        *,
        session: ClientSession,
        http_client: BaseRateLimiterHttpClient,
        instrument_manager: BaseInstrumentManager,
        logger: Logger = null_logger(),
    ) -> None:
        super().__init__(
            session=session,
            http_client=http_client,
            instrument_manager=instrument_manager,
            logger=logger,
        )
        self.containers: dict[str, KlinesContainer] = {}

    @property
    @abstractmethod
    def rest_limit(self) -> int: ...

    def __getitem__(self, symbol: str) -> KlinesContainer:
        if symbol not in self.containers:
            self.containers[symbol] = KlinesContainer()
        return self.containers[symbol]
