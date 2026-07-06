import asyncio
import time
from typing import Type
import numpy as np

from connector.connector import BaseConnector
from connector.http_client import make_session
from connector.async_logger import make_async_logger
from connector.notification import Notification
from connector.utils import traceback_error_str
from connector.binance.binance_perp import BinancePerp
from connector.binance.binance_spot import BinanceSpot


class Monitor:
    def __init__(self, connector_type_list: list[Type[BaseConnector]]) -> None:
        self.logger = make_async_logger("m")
        self.connectors: dict[Type[BaseConnector], BaseConnector] = {}
        self.connector_type_list = connector_type_list
        self.z_level: float = 10
        self.perc_level: float = 0.01
        self.s_perc_level: float = 0.002

    async def loop_lag_monitor(self, period: float = 0.05, threshold_ms: float = 10):
        while True:
            next = time.perf_counter() + period
            next_t = time.thread_time() + period
            await asyncio.sleep(period)
            now = time.perf_counter()
            now_t = time.thread_time()

            lag_ms = max(0.0, (now - next) * 1000)
            lagt_ms = max(0.0, (now_t - next_t) * 1000)
            if lag_ms >= threshold_ms:
                self.logger.warning(f"event loop spike: {lag_ms:.1f} ms, thread: {lagt_ms:.1f} ms")

    async def loop_check_signals(self) -> None:
        try:
            informed: dict[str, int] = {}
            window = 1440
            while True:
                await asyncio.sleep(5)
                for symbol, container in self.connectors[BinancePerp].kline_service.containers.items():
                    if container.klines_1m.wrapped:
                        await asyncio.sleep(0)
                        ts, p, n, _ = container.klines_1m.ordered()
                        nc = n[:-1][-window:]  # закрытые бары

                        med = np.median(nc)
                        sigma = 1.4826 * np.median(np.abs(nc - med))
                        z = round((n[-1] - med) / sigma, 1)
                        perc = round(p[-1] / p[-2] - 1, 3)
                        click_url = f"https://www.coinglass.com/tv/Binance_{symbol}"

                        if ts[-1] > informed.get(symbol, 0) and z > self.z_level and perc > self.perc_level:
                            informed[symbol] = ts[-1]
                            tag = "green_circle" if perc > 0 else "red_circle"
                            await self.notification.send(f"{symbol} z: {z:.1f}, perc: {perc*100:.1f}%, price: {p[-1]}", tags=tag, click_url=click_url)

                        if ts[-1] - informed.get(symbol, 0) > 1000 * 60 * 60 and symbol in self.connectors[BinanceSpot].kline_service.containers:
                            try:
                                sts, sp, _, _ = self.connectors[BinanceSpot].kline_service[symbol].klines_1m.ordered()
                                diff = sp[-1] / p[-1] - 1
                                s_perc = round(sp[-1] / sp[-2] - 1, 3)

                                if ts[-1] == sts[-1] and diff > 0.01 and s_perc > self.s_perc_level:
                                    await self.notification.send(
                                        f"{symbol} diff: {diff*100:.1f}%, s_perc: {s_perc*100:.1f}, price: {p[-1]}, time: {ts[-1] - informed.get(symbol, 0)}",
                                        click_url=click_url,
                                    )
                                    informed[symbol] = ts[-1]
                            except:
                                self.logger.error(f"symbol: {symbol}, sp: {sp}")
        except Exception:
            self.logger.error(traceback_error_str())
            raise

    async def run(self) -> None:
        try:
            async with make_session() as session:
                self.notification = Notification(session)
                cpu_sem = asyncio.Semaphore(8)

                for connector_type in self.connector_type_list:
                    connector = connector_type(
                        session=session,
                        logger=self.logger,
                        cpu_sem=cpu_sem,
                    )
                    self.connectors[connector_type] = connector

                async with asyncio.TaskGroup() as tg:
                    tg.create_task(self.loop_lag_monitor())
                    tg.create_task(self.loop_check_signals())

                    for connector in self.connectors.values():
                        tg.create_task(connector.run())
        except asyncio.CancelledError:
            self.logger.info("Monitor stopped (CancelledError)")
        except Exception:
            self.logger.error(traceback_error_str())
