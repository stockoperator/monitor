import asyncio
import time
import numpy as np
from typing import Type

from connector.connector import BaseConnector
from connector.http_client import make_session
from connector.async_logger import make_async_logger
from connector.notification import Notification
from connector.utils import traceback_error_str
from connector.binance.binance_perp import BinancePerp


class Monitor:
    def __init__(self, connector_type_list: list[Type[BaseConnector]]) -> None:
        self.logger = make_async_logger("m")
        self.connectors: dict[Type[BaseConnector], BaseConnector] = {}
        self.connector_type_list = connector_type_list

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
            while True:
                await asyncio.sleep(5)
                for con_type, connector in self.connectors.items():
                    for instrument in connector.instrument_manager.values():
                        symbol = instrument.exchange_symbol
                        public_trades = connector.kline_service[symbol].klines_1m
                        volumes = public_trades.notionals
                        idx = public_trades.idx
                        idx1 = idx + 1
                        size = len(public_trades)
                        t = public_trades.timestamps[idx]
                        if t > informed.get(symbol, 0) and size == public_trades.size:
                            v = np.concatenate([volumes[:idx], volumes[idx1:size]])
                            vc = volumes[idx]
                            k = vc / np.max(v)
                            perc = (public_trades.prices[idx] / public_trades.prices[idx - 1] - 1) * 100.0
                            if k > 2.0 and perc > 0.0 and self.connectors[BinancePerp].instrument_manager.get(instrument.unified_symbol):
                                informed[symbol] = t
                                tag = "green_circle" if perc > 0 else "red_circle"
                                await self.notification.send(f"{con_type.__name__} {symbol} volume_k: {k:.1f}, vol: {vc:0.1f}, perc: {perc:.1f}", tags=tag)
        except Exception:
            self.logger.error(traceback_error_str())
            raise

    async def run(self) -> None:
        try:
            async with make_session() as session:
                self.notification = Notification(session)

                for connector_type in self.connector_type_list:
                    connector = connector_type(
                        session=session,
                        logger=self.logger,
                    )
                    self.connectors[connector_type] = connector

                async with asyncio.TaskGroup() as tg:
                    tg.create_task(self.loop_lag_monitor())
                    # tg.create_task(self.loop_check_signals())

                    for connector in self.connectors.values():
                        tg.create_task(connector.run())
        except asyncio.CancelledError:
            self.logger.info("Monitor stopped (CancelledError)")
        except Exception:
            self.logger.error(traceback_error_str())
