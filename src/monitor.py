import asyncio
import time
from typing import Type
import os
import uvloop


from connector.binance.binance_perp import BinancePerp
from connector.binance.binance_spot import BinanceSpot
from connector.connector import BaseConnector
from connector.http_client import make_session
from connector.async_logger import AsyncLogger
from connector.utils import traceback_error_str

asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())


class Monitor:
    def __init__(self, connector_type_list: list[Type[BaseConnector]]) -> None:
        self.logger = AsyncLogger("m").get_logger()
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

    async def run(self) -> None:
        try:
            async with make_session() as session:
                for connector_type in self.connector_type_list:
                    connector = connector_type(session=session, logger=self.logger)
                    self.connectors[connector_type] = connector
                async with asyncio.TaskGroup() as tg:
                    tg.create_task(self.loop_lag_monitor())

                    for connector in self.connectors.values():
                        tg.create_task(connector.run())
        except asyncio.CancelledError:
            self.logger.info("Monitor stopped (CancelledError)")
        except Exception:
            self.logger.error(traceback_error_str())


if __name__ == "__main__":
    print(f"PID: {os.getpid()}")
    connector_type_list: list[Type[BaseConnector]] = [BinancePerp, BinanceSpot]
    m = Monitor(connector_type_list=connector_type_list)
    # gc.disable()
    asyncio.run(m.run())
