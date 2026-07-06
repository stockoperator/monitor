from abc import ABC, abstractmethod
from logging import Logger
from aiohttp import ClientSession
from typing import Type


from connector.async_logger import null_logger
from connector.rate_limiter import BaseRateLimiterHttpClient
from connector.instrument import BaseInstrumentManager
from connector.utils import traceback_error_str


class BaseRestDataService(ABC):
    def __init__(
        self,
        *,
        session: ClientSession,
        http_client: BaseRateLimiterHttpClient,
        instrument_manager: BaseInstrumentManager,
        logger: Logger = null_logger(),
    ) -> None:
        self.logger = logger
        self.http_client = http_client

        self.instrument_manager = instrument_manager

        self.data = self.data_type()

    @property
    @abstractmethod
    def data_type(self) -> Type(object): ...

    def get(self, key: str, default: None = None) -> Instrument | None:
        return self.instruments.get(key, default)

    def __getitem__(self, symbol: str) -> Instrument:
        return self.instruments[symbol]

    def values(self):
        return self.instruments.values()

    @property
    @abstractmethod
    def url(self) -> str: ...

    @abstractmethod
    def instruments_info(self, exchange_info: Any) -> list[dict[str, Any]]: ...

    @property
    @abstractmethod
    def instrument_validation_dict(self) -> dict[str, Any]: ...

    @abstractmethod
    def make_instrument_from_instrument_info(self, instrument_info: dict[str, Any]) -> Instrument: ...

    @abstractmethod
    async def update_leverage_brackets(self) -> None: ...

    async def get_exchange_info(self) -> dict[str, Any]:
        response = await self.http_client.request(method=HTTPMethod.GET, url=self.exchange_info_url)
        return response.data

    async def fetch_instruments(self) -> dict[str, Instrument]:
        instruments: dict[str, Instrument] = {}
        exchange_info = await self.get_exchange_info()

        for instrument_info in self.instruments_info(exchange_info):
            if validate_dict_by_dict(instrument_info, self.instrument_validation_dict):
                instrument = self.make_instrument_from_instrument_info(instrument_info)
                instruments[instrument.unified_symbol] = instrument
        return instruments

    def publish(self, event: Event) -> None:
        for queue in self.subscribers:
            queue.put_nowait(event)

    async def update_instruments(self) -> None:
        new_items = await self.fetch_instruments()

        old_keys = set(self.instruments.keys())
        new_keys = set(new_items.keys())

        added_keys = new_keys - old_keys
        removed_keys = old_keys - new_keys
        common_keys = old_keys & new_keys

        for key in common_keys:
            self.instruments[key] = new_items[key]

        new_exchange_symbols: set[str] = set()
        for key in added_keys:
            instrument = new_items[key]
            self.instruments[key] = instrument
            new_exchange_symbols.add(instrument.exchange_symbol)

        for key in removed_keys:
            self.instruments.pop(key)

        if new_exchange_symbols:
            self.publish(InstrumentAddedEvent(new_exchange_symbols))
            if old_keys:
                self.logger.info(f"new instruments added: {added_keys}")

        await self.update_leverage_brackets()

    async def update_instruments_loop(self) -> None:
        await run_periodic("update-instruments", 60 * self.update_interval, self.update_instruments, self.logger)

