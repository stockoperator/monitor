from abc import ABC, abstractmethod
import asyncio
from aiohttp import ClientSession
from typing import Type
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
        session: ClientSession,
        api_key: str = "",
        secret_key: str = "",
        passphrase: str = "",
        logger: logging.Logger = null_logger(),
    ) -> None:
        self.api_key = api_key
        self.secret_key = secret_key
        self.passphrase = passphrase

        self.logger = logger.getChild(self.__class__.__name__)

        self.http_client = self.http_client_type(session)

        self.instruments = self.instrument_manager_type(
            self.http_client,
            name=self.name,
            market_type=self.market_type,
            logger=self.logger.getChild("instruments"),
        )
        self.orderbooks = self.orderbook_service_type(
            session=session,
            instruments=self.instruments,
            logger=self.logger.getChild("orderbook"),
        )

        self.public_trades = self.public_trade_service_type(
            session=session,
            instruments=self.instruments,
            logger=self.logger.getChild("public_trades"),
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
        await self.instruments.update_instruments()

        async with asyncio.TaskGroup() as tg:
            tg.create_task(self.instruments.update_instruments_loop())
            tg.create_task(self.orderbooks.run())
            tg.create_task(self.public_trades.run())
