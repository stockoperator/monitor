import asyncio
import time
from dataclasses import dataclass
from logging import Logger
from typing import Any
from abc import ABC, abstractmethod

from connector.async_logger import null_logger
from connector.http_client import BaseHttpClient, HTTPMethod, HttpResponse


@dataclass(kw_only=True, eq=False, slots=True)
class LimitWindow:
    weight_limit: int
    window_seconds: int
    response_header: str
    used_weight: int = 0
    last_request_time: float = 0
    safety_margin: float = 0.10

    def is_blocking(self) -> bool:
        return int(self.last_request_time / self.window_seconds) == int(time.time() / self.window_seconds) and (
            self.used_weight >= (1 - self.safety_margin) * self.weight_limit
        )

    def update(self, used_weight: int) -> None:
        self.used_weight = used_weight
        self.last_request_time = time.time()


class BaseRateLimiterHttpClient(ABC):
    def __init__(
        self,
        *,
        http_client: BaseHttpClient,
        limit_windows: list[LimitWindow] | None = None,
        max_concurrency: int = 100,
        logger: Logger = null_logger(),
    ) -> None:
        self.http_client = http_client
        self.limit_windows = limit_windows if limit_windows else []
        self._max_concurrency = max_concurrency
        self._logger = logger
        self._condition = asyncio.Condition()
        self._in_flight: int = 0
        self._retry_after: float = 0.0

    @abstractmethod
    def update_limits(self, response: HttpResponse) -> None: ...

    def target_concurrency(self) -> int:
        max_concurrency = self._max_concurrency
        for limit_window in self.limit_windows:
            if limit_window.used_weight == 0:
                return 1
            else:
                max_concurrency = min(max_concurrency, self._max_concurrency * (1 - limit_window.used_weight / limit_window.weight_limit))
        return int(max_concurrency)

    def freeze_remaining(self) -> float | None:
        now = time.monotonic()
        if self._retry_after > now:
            return self._retry_after - now

        time_out = 60
        for w in self.limit_windows:
            if w.is_blocking():
                time_out = min(time_out, w.window_seconds - (w.last_request_time % w.window_seconds) + 1)

        return time_out

    def can_admit(self) -> bool:
        if time.monotonic() < self._retry_after:
            return False
        if self._in_flight >= self.target_concurrency():
            return False

        for limit_window in self.limit_windows:
            if limit_window.is_blocking():
                return False

        return True

    async def request(
        self,
        method: HTTPMethod,
        url: str,
        params: dict[str, Any] | None = None,
        is_auth_required: bool = False,
    ) -> HttpResponse:
        async with self._condition:
            while not self.can_admit():
                freeze_left = self.freeze_remaining()
                try:
                    await asyncio.wait_for(self._condition.wait(), timeout=freeze_left)
                except asyncio.TimeoutError:
                    pass
        try:
            self._in_flight += 1
            response = await self.http_client.request(method=method, url=url, params=params, is_auth_required=is_auth_required)
            self.update_limits(response)
        finally:
            async with self._condition:
                self._in_flight -= 1
                self._condition.notify(n=self._max_concurrency)

        return response
