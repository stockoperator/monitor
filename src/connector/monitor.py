import asyncio
import time
from typing import Type

from connector.connector import BaseConnector
from connector.http_client import make_session
from connector.async_logger import make_async_logger
from connector.notification import Notification
from connector.utils import traceback_error_str
from connector.utils_io import save_all_trade_data, load_all_trade_data


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

    async def loop_save_trades(self):
        while True:
            await asyncio.sleep(60)
            await save_all_trade_data(self.connectors)

    async def run(self) -> None:
        try:
            async with make_session() as session:
                self.notification = Notification(session)

                for connector_type in self.connector_type_list:
                    connector = connector_type(session=session, logger=self.logger)
                    self.connectors[connector_type] = connector

                try:
                    await load_all_trade_data(self.connectors)
                    self.logger.info("TradeContainer data successfully restored.")
                except FileNotFoundError:
                    self.logger.warning("Snapshot file not found. Using empty state.")
                except Exception:
                    self.logger.error("Error while loading data:\n%s", traceback_error_str())

                async with asyncio.TaskGroup() as tg:
                    tg.create_task(self.loop_lag_monitor())
                    tg.create_task(self.loop_save_trades())

                    for connector in self.connectors.values():
                        tg.create_task(connector.run())
        except asyncio.CancelledError:
            self.logger.info("Monitor stopped (CancelledError)")
        except Exception:
            self.logger.error(traceback_error_str())
        finally:
            try:
                await save_all_trade_data(self.connectors)
                self.logger.info("TradeContainer data successfully saved.")
            except Exception:
                self.logger.error(traceback_error_str())
