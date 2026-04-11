from abc import ABC, abstractmethod
import asyncio
from aiohttp import ClientSession
from typing import Type
import os
import logging

from connector.async_logger import null_logger
from connector.http_client import BaseHttpClient
from connector.base_classes import ExchangeName, MarketType
from connector.instrument import BaseInstrumentManager
from connector.orderbook_service import BaseOrderbookService
from connector.public_trade_service import BasePublicTradeService


class BaseConnector(ABC):
    def __init__(
        self,
        *,
        session: ClientSession,
        api_key: str = "",
        secret_key: str = "",
        passphrase: str = "",
        logger: logging.Logger = null_logger(),
    ) -> None:
        self.api_key = api_key if api_key else os.getenv(f"{self.name.value.upper()}_API_KEY", "")
        self.secret_key = secret_key if secret_key else os.getenv(f"{self.name.value.upper()}_SECRET_KEY", "")
        self.passphrase = passphrase if passphrase else os.getenv(f"{self.name.value.upper()}_PASSPHRASE", "")

        self.logger = logger.getChild(self.__class__.__name__)

        self.http_client = self.http_client_type(
            session=session,
            api_key=self.api_key,
            secret_key=self.secret_key,
            passphrase=self.passphrase,
            logger=self.logger.getChild("http"),
        )

        self.instrument_manager = self.instrument_manager_type(
            http_client=self.http_client,
            logger=self.logger.getChild("instruments"),
        )
        self.orderbook_service = self.orderbook_service_type(
            session=session,
            instruments=self.instrument_manager,
            logger=self.logger.getChild("orderbook"),
        )

        self.trade_service = self.public_trade_service_type(
            session=session,
            instruments=self.instrument_manager,
            logger=self.logger.getChild("trade_container"),
        )

    @property
    @abstractmethod
    def http_client_type(self) -> Type[BaseHttpClient]: ...

    @property
    @abstractmethod
    def instrument_manager_type(self) -> Type[BaseInstrumentManager]: ...

    @property
    @abstractmethod
    def orderbook_service_type(self) -> Type[BaseOrderbookService]: ...

    @property
    @abstractmethod
    def public_trade_service_type(self) -> Type[BasePublicTradeService]: ...

    @property
    @abstractmethod
    def name(self) -> ExchangeName: ...

    @property
    @abstractmethod
    def market_type(self) -> MarketType: ...

    async def run(self) -> None:
        await self.instrument_manager.update_instruments()

        async with asyncio.TaskGroup() as tg:
            tg.create_task(self.instrument_manager.update_instruments_loop())
            tg.create_task(self.trade_service.run())
            # tg.create_task(self.orderbooks.run())
