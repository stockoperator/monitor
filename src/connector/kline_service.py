import asyncio
from logging import Logger
from aiohttp import ClientSession
import numpy as np
from datetime import datetime, timezone
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
        "close_prices",
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
        self.close_prices = np.zeros(size, dtype=np.float64)
        self.notionals = np.zeros(size, dtype=np.float64)
        self.delta_notionals = np.zeros(size, dtype=np.float64)
        self.closed_notional: float = 0
        self.closed_delta_notional: float = 0
        self.last_timestamp: int = 0

    def __len__(self) -> int:
        return self.size if self.wrapped else self.idx + 1

    def set(self, timestamp: int, close_price: float, notional: float, delta_notional: float) -> None:
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

        self.close_prices[self.idx] = close_price
        self.notionals[self.idx] = notional + self.closed_notional
        self.delta_notionals[self.idx] = delta_notional + self.closed_delta_notional

    def ordered(
        self,
        from_date_utc: str | None = None,
        to_date_utc: str | None = None,
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        size = len(self)
        split_idx = self.idx + 1
        ts = np.concatenate((self.timestamps[split_idx:size], self.timestamps[:split_idx]))
        p = np.concatenate((self.close_prices[split_idx:size], self.close_prices[:split_idx]))
        n = np.concatenate((self.notionals[split_idx:size], self.notionals[:split_idx]))
        dn = np.concatenate((self.delta_notionals[split_idx:size], self.delta_notionals[:split_idx]))

        if from_date_utc or to_date_utc:
            if from_date_utc:
                left_ms = int(datetime.fromisoformat(from_date_utc).replace(tzinfo=timezone.utc).timestamp() * 1000)
                i = np.searchsorted(ts, left_ms, side="left")
            else:
                i = 0
            if to_date_utc:
                right_ms = int(datetime.fromisoformat(to_date_utc).replace(tzinfo=timezone.utc).timestamp() * 1000)
                j = np.searchsorted(ts, right_ms, side="right")
            else:
                j = size

            ts, p, n, dn = ts[i:j], p[i:j], n[i:j], dn[i:j]

        return ts, p, n, dn


class KlinesContainer:
    __slots__ = ("klines_1m", "klines_1h", "klines_1d")

    def __init__(self, size_1m: int = 1440, size_1h: int = 1440, size_1d: int = 1440) -> None:
        self.klines_1m = Klines(size=size_1m, period_sec=60)
        self.klines_1h = Klines(size=size_1h, period_sec=60 * 60)
        self.klines_1d = Klines(size=size_1d, period_sec=60 * 60 * 24)

    def set(self, timestamp: int, close_price: float, notional: float, delta_notional: float) -> None:
        for slot in self.__slots__:
            klines: Klines = getattr(self, slot)
            klines.set(timestamp, close_price, notional, delta_notional)


class BaseKlineService(BaseDataService):
    def __init__(
        self,
        *,
        session: ClientSession,
        http_client: BaseRateLimiterHttpClient,
        instrument_manager: BaseInstrumentManager,
        logger: Logger = null_logger(),
        cpu_sem: asyncio.Semaphore,
    ) -> None:
        super().__init__(
            session=session,
            http_client=http_client,
            instrument_manager=instrument_manager,
            logger=logger,
        )
        self.containers: dict[str, KlinesContainer] = {}
        self.cpu_sem = cpu_sem

    @property
    @abstractmethod
    def rest_limit(self) -> int: ...

    def __getitem__(self, symbol: str) -> KlinesContainer:
        if symbol not in self.containers:
            self.containers[symbol] = KlinesContainer()
        return self.containers[symbol]
