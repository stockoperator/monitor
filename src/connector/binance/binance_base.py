import hmac
import time
from typing import Any
import orjson
import numpy as np
from abc import ABC, abstractmethod
import asyncio

from connector.connector import BaseConnector
from connector.base_classes import ExchangeName
from connector.kline_service import BaseKlineService, Klines
from connector.http_client import BaseHttpClient, HTTPMethod, HttpResponse
from connector.rate_limiter import BaseRateLimiterHttpClient
from connector.instrument import BaseInstrumentManager
from connector.utils import traceback_error_str


class BinanceApiError(RuntimeError):
    pass


def raise_for_status(response: HttpResponse, context: str) -> None:
    """Raise BinanceApiError on non-200. Surfaces Binance's `code`/`msg` from the payload."""
    if response.status == 200:
        return
    data: dict[str, Any] = response.data
    raise BinanceApiError(f"{context}: status: {response.status}, code: {data.get('code')}, msg: {data.get('msg')!r}")


class BinanceHttpClientBase(BaseHttpClient):
    def _sign(self, message: str) -> str:
        return hmac.new(key=self.secret_key.encode("utf-8"), msg=message.encode("utf-8"), digestmod="sha256").hexdigest()

    async def request(self, method: HTTPMethod, url: str, params: dict[str, Any] | None = None, is_auth_required: bool = False) -> HttpResponse:
        params = params if params else {}
        headers = {}

        if is_auth_required:
            headers = {"X-MBX-APIKEY": self.api_key}
            params["timestamp"] = int((time.time() - 10) * 1000)
            params["recvWindow"] = 50000

            query_str = "&".join(f"{k}={v}" for k, v in params.items())
            params["signature"] = self._sign(query_str)

        async with self.session.request(method=method.value, url=url, params=params, headers=headers) as response:
            r = await response.read()
            data = orjson.loads(r)

            return HttpResponse(
                data=data,
                status=response.status,
                headers=response.headers,
            )


class BinanceBaseInstrumentManager(BaseInstrumentManager):
    def instruments_info(self, exchange_info: Any) -> list[dict[str, Any]]:
        return exchange_info["symbols"]


class BinanceBase(BaseConnector):
    @property
    def name(self) -> ExchangeName:
        return ExchangeName.BINANCE


class BinanceBaseKlineService(BaseKlineService, ABC):
    @property
    @abstractmethod
    def ws_url(self) -> str: ...

    @property
    @abstractmethod
    def klines_url(self) -> str: ...

    def get_channel(self, symbol: str) -> str:
        return f"{symbol.lower()}@kline_1m"

    def make_subscribe_message(self, channel_batch: list[str]) -> bytes:
        return orjson.dumps({"method": "SUBSCRIBE", "params": channel_batch})

    def handle_message(self, message: str) -> None:
        data: dict[str, Any] = orjson.loads(message)
        if data.get("e") != "kline":
            return

        k = data["k"]
        if k.get("i") != "1m":
            return

        symbol = str(data["s"])
        open_time = int(k["t"])
        close_price = float(k["c"])
        notional = float(k["q"])
        taker_buy = float(k["Q"])
        delta_notional = 2.0 * taker_buy - notional

        container = self[symbol]

        t0 = time.perf_counter_ns()
        container.set(open_time, close_price, notional, delta_notional)
        wall_ms = (time.perf_counter_ns() - t0) / 1e6
        if wall_ms >= 2:
            self.logger.info("kline append wall=%.1f ms symbol=%s", wall_ms, symbol)

    async def fetch_historical_bars(self, symbol: str, timeframe: str, end_time: int, size: int) -> list[list[Any]]:
        bars: list[list[Any]] = []
        params: dict[str, Any] = {"symbol": symbol, "interval": timeframe, "endTime": end_time, "limit": self.rest_limit}
        while params["limit"]:
            response = await self.http_client.request(HTTPMethod.GET, self.klines_url, params=params)
            batch = response.data
            if not batch:
                break

            bars = batch + bars
            params["endTime"] = int(batch[0][0]) - 1
            params["limit"] = min(self.rest_limit, size - len(bars))
        return bars

    def bars_to_arrays(self, bars: list[list[Any]]) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        ts = np.array([bar[0] for bar in bars], dtype=np.int64)
        prices = np.array([bar[4] for bar in bars], dtype=np.float64)
        notionals = np.array([bar[7] for bar in bars], dtype=np.float64)
        buy_notionals = np.array([bar[10] for bar in bars], dtype=np.float64)
        delta_notional = 2.0 * buy_notionals - notionals
        return ts, prices, notionals, delta_notional

    async def fill_symbol_frame(self, symbol: str, timeframe: str, closed_timeframe: str = "") -> None:
        kline_container = self[symbol]
        klines: Klines = getattr(kline_container, f"klines_{timeframe}")
        size = klines.size

        while klines.idx == -1:
            await asyncio.sleep(1)

        if 0 < len(klines) < size:
            first_idx = (klines.idx + 1) % klines.size if klines.wrapped else 0
            ws_start_time = int(klines.timestamps[first_idx]) - 1

            bars = await self.fetch_historical_bars(symbol=symbol, timeframe=timeframe, end_time=ws_start_time, size=size)
            if not bars:
                return

            ts_new, prices_new, notionals_new, delta_notional_new = self.bars_to_arrays(bars)

            t_existing, p_existing, n_existing, d_existing = klines.ordered()

            if closed_timeframe:
                klines_closed: Klines = getattr(kline_container, f"klines_{closed_timeframe}")

                t_closed, _, n_closed, d_closed = klines_closed.ordered()
                current_mask = t_closed >= t_existing[-1]
                klines.closed_notional = np.sum(n_closed[current_mask][:-1])
                klines.closed_delta_notional = np.sum(d_closed[current_mask][:-1])

                if len(klines) > 1:
                    # First WS bar is partial (WS connected mid-period); rebuild it from the lower timeframe.
                    first_mask = (t_closed >= t_existing[0]) & (t_closed < t_existing[1])
                    n_existing[0] = np.sum(n_closed[first_mask])
                    d_existing[0] = np.sum(d_closed[first_mask])

            ts = np.concatenate((ts_new, t_existing))[-size:]
            prices = np.concatenate((prices_new, p_existing))[-size:]
            notionals = np.concatenate((notionals_new, n_existing))[-size:]
            delta_notional = np.concatenate((delta_notional_new, d_existing))[-size:]

            fill_len = len(ts)
            klines.timestamps[:fill_len] = ts
            klines.prices[:fill_len] = prices
            klines.notionals[:fill_len] = notionals
            klines.delta_notionals[:fill_len] = delta_notional

            klines.idx = fill_len - 1
            klines.wrapped = False

    async def fill_symbol(self, symbol: str) -> None:
        closed_timeframe = ""
        for timeframe in ["1m", "1h", "1d"]:
            await self.fill_symbol_frame(symbol, timeframe, closed_timeframe)
            closed_timeframe = timeframe

    async def fill(self, symbols: set[str]) -> None:
        try:
            self.logger.info(f"klines download started")
            tasks = [self.fill_symbol(symbol) for symbol in symbols]
            await asyncio.gather(*tasks)
            self.logger.info(f"klines download finished")
        except Exception:
            self.logger.error(traceback_error_str())

    async def handle_instruments_added(self, symbols: set[str]) -> None:
        asyncio.create_task(self.fill(symbols))


class BinanceBasePublicRateLimiter(BaseRateLimiterHttpClient):
    def update_limits(self, response: HttpResponse) -> None:
        for window in self.limit_windows:
            raw = response.headers.get(window.response_header)
            if raw:
                window.update(int(raw))

        if response.status in (418, 429):
            wait_sec = float(response.headers.get("Retry-After", 0))
            self._retry_after = time.monotonic() + wait_sec
            for window in self.limit_windows:
                window.update(window.weight_limit)
            self._logger.error("binance rate limit hit status: %d, freeze: %.1fs", response.status, wait_sec)
