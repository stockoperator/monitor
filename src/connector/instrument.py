from abc import ABC, abstractmethod
from typing import Any
from dataclasses import dataclass
import asyncio
import logging

from connector.http_client import BaseHttpClient, HTTPMethod
from connector.utils import traceback_error_str, validate_dict_by_dict
from connector.async_logger import null_logger
from connector.events import Event, InstrumentAddedEvent


@dataclass(kw_only=True, eq=False, slots=True)
class Instrument:
    exchange_symbol: str  # биржевое имя: "BTC-USDT или BTC_USDT"
    unified_symbol: str  # унифицированное: "BTCUSDT"
    min_price: float | None = None
    max_price: float | None = None
    price_step: float | None = None
    min_qty: float | None = None
    max_qty: float | None = None
    qty_step: float | None = None


class BaseInstrumentManager(ABC):
    def __init__(
        self,
        *,
        http_client: BaseHttpClient,
        logger: logging.Logger = null_logger(),
        update_interval: int = 30,  # min
    ) -> None:
        self.http_client = http_client
        self.logger = logger
        self.update_interval = update_interval
        self.on_instruments_added: set[asyncio.Queue[Event]] = set()

        self._items: dict[str, Instrument] = {}

    def __getitem__(self, symbol: str) -> Instrument:
        return self._items[symbol]

    def values(self):
        return self._items.values()

    @property
    @abstractmethod
    def exchange_info_url(self) -> str: ...

    @abstractmethod
    def instruments_info(self, exchange_info: Any) -> list[dict[str, Any]]: ...

    @property
    @abstractmethod
    def instrument_validation_dict(self) -> dict[str, Any]: ...

    @abstractmethod
    def make_instrument_from_instrument_info(self, instrument_info: dict[str, Any]) -> Instrument: ...

    async def get_exchange_info(self) -> dict[str, Any]:
        return await self.http_client.request(method=HTTPMethod.GET, url=self.exchange_info_url)

    async def fetch_instruments(self) -> dict[str, Instrument]:
        instruments: dict[str, Instrument] = {}
        exchange_info = await self.get_exchange_info()

        for instrument_info in self.instruments_info(exchange_info):
            if validate_dict_by_dict(instrument_info, self.instrument_validation_dict):
                instrument = self.make_instrument_from_instrument_info(instrument_info)
                instruments[instrument.unified_symbol] = instrument
        return instruments

    async def update_instruments(self) -> None:
        try:
            new_items = await self.fetch_instruments()

            old_keys = set(self._items.keys())
            new_keys = set(new_items.keys())

            added_keys = new_keys - old_keys
            removed_keys = old_keys - new_keys
            common_keys = old_keys & new_keys

            for key in common_keys:
                self._items[key] = new_items[key]

            new_exchange_symbols: set[str] = set()
            for key in added_keys:
                instrument = new_items[key]
                self._items[key] = instrument
                new_exchange_symbols.add(instrument.exchange_symbol)

            removed_exchange_symbols: set[str] = set()
            for key in removed_keys:
                instrument = self._items.pop(key)
                removed_exchange_symbols.add(instrument.exchange_symbol)

            if new_exchange_symbols:
                for queue in self.on_instruments_added:
                    queue.put_nowait(InstrumentAddedEvent(new_exchange_symbols))

        except NotImplementedError:
            raise
        except asyncio.CancelledError:
            raise
        except Exception:
            self.logger.error(traceback_error_str())
            await asyncio.sleep(5)

    async def update_instruments_loop(self):
        while True:
            await asyncio.sleep(60 * self.update_interval)
            await self.update_instruments()
