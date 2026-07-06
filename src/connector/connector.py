from abc import ABC, abstractmethod
import asyncio
from aiohttp import ClientSession
from typing import Type
import os
import logging
from pathlib import Path

from connector.async_logger import null_logger
from connector.http_client import BaseHttpClient
from connector.rate_limiter import BaseRateLimiterHttpClient
from connector.base_classes import ExchangeName, MarketType
from connector.instrument import BaseInstrumentManager
from connector.kline_service import BaseKlineService
from connector.funding_service import BaseFundingService
from connector.account_service import BaseAccountService
from connector.utils import traceback_error_str


class BaseConnector(ABC):
    def __init__(
        self,
        *,
        session: ClientSession,
        api_key: str = "",
        secret_key: str = "",
        passphrase: str = "",
        logger: logging.Logger = null_logger(),
        cpu_sem: asyncio.Semaphore,
    ) -> None:
        self.api_key = api_key if api_key else os.getenv(f"{self.name.value.upper()}_API_KEY", "")
        self.secret_key = secret_key if secret_key else os.getenv(f"{self.name.value.upper()}_SECRET_KEY", "")
        self.passphrase = passphrase if passphrase else os.getenv(f"{self.name.value.upper()}_PASSPHRASE", "")

        self.logger = logger.getChild(self.__class__.__name__)
        self.cpu_sem = cpu_sem

        http_client = self.http_client_type(
            session=session,
            api_key=self.api_key,
            secret_key=self.secret_key,
            passphrase=self.passphrase,
            logger=self.logger.getChild("http"),
        )

        self.public_http_client = self.public_http_client_type(
            http_client=http_client,
        )

        self.order_http_client = self.order_http_client_type(
            http_client=http_client,
        )

        self.instrument_manager = self.instrument_manager_type(
            http_client=self.public_http_client,
            logger=self.logger.getChild("instruments"),
        )

        self.kline_service = self.kline_service_type(
            session=session,
            http_client=self.public_http_client,
            instrument_manager=self.instrument_manager,
            logger=self.logger.getChild("klines"),
            cpu_sem=cpu_sem,
        )

        if self.funding_service_type:
            self.funding_service = self.funding_service_type(
                session=session,
                http_client=self.public_http_client,
                instrument_manager=self.instrument_manager,
                logger=self.logger.getChild("funding"),
            )
        else:
            self.funding_service = None

        if self.account_service_type:
            self.account_service = self.account_service_type(
                session=session,
                logger=self.logger.getChild("account"),
                state_path=Path("data") / f"{self.name.value}_{self.market_type.value}.json",
                http_client=self.public_http_client,
                order_http_client=self.order_http_client,
            )
        else:
            self.account_service = None

    @property
    @abstractmethod
    def http_client_type(self) -> Type[BaseHttpClient]: ...

    @property
    @abstractmethod
    def public_http_client_type(self) -> Type[BaseRateLimiterHttpClient]: ...

    @property
    @abstractmethod
    def order_http_client_type(self) -> Type[BaseRateLimiterHttpClient]: ...

    @property
    @abstractmethod
    def instrument_manager_type(self) -> Type[BaseInstrumentManager]: ...

    @property
    @abstractmethod
    def kline_service_type(self) -> Type[BaseKlineService]: ...

    @property
    def funding_service_type(self) -> Type[BaseFundingService] | None:
        return None

    @property
    @abstractmethod
    def account_service_type(self) -> Type[BaseAccountService] | None: ...

    @property
    @abstractmethod
    def name(self) -> ExchangeName: ...

    @property
    @abstractmethod
    def market_type(self) -> MarketType: ...

    async def run(self) -> None:
        try:
            await self.instrument_manager.update_instruments()

            async with asyncio.TaskGroup() as tg:
                tg.create_task(self.instrument_manager.update_instruments_loop())
                tg.create_task(self.kline_service.run())
                if self.funding_service is not None:
                    tg.create_task(self.funding_service.run())
                if self.account_service is not None:
                    tg.create_task(self.account_service.run())
        except* asyncio.CancelledError:
            self.logger.info("Монитор остановлен (CancelledError)")
        except* Exception:
            self.logger.error(traceback_error_str())
