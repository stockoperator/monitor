from abc import ABC, abstractmethod
from typing import Any
from dataclasses import dataclass, field
import asyncio
import logging

from connector.http_client import HTTPMethod
from connector.rate_limiter import BaseRateLimiterHttpClient
from connector.utils import run_periodic, validate_dict_by_dict
from connector.async_logger import null_logger
from connector.events import Event, InstrumentAddedEvent


@dataclass(kw_only=True, eq=False, slots=True)
class LeverageBracket:
    initial_leverage: float
    maint_margin_ratio: float
    notional_floor: int
    notional_cap: int
    cumulative_amount: int


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
    min_notional: float | None = None
    liquidation_fee: float | None = None
    leverage_brackets: tuple[LeverageBracket, ...] = field(default_factory=tuple)

    def find_leverage_bracket(self, notional: float) -> LeverageBracket:
        for bracket in self.leverage_brackets:
            if bracket.notional_floor <= notional < bracket.notional_cap:
                return bracket

        raise ValueError(f"No leverage bracket found for {self.unified_symbol}, notional: {notional}")


class BaseInstrumentManager(ABC):
    def __init__(
        self,
        *,
        http_client: BaseRateLimiterHttpClient,
        logger: logging.Logger = null_logger(),
        update_interval: int = 30,  # min
    ) -> None:
        self.http_client = http_client
        self.logger = logger
        self.update_interval = update_interval
        self.subscribers: set[asyncio.Queue[Event]] = set()

        self.instruments: dict[str, Instrument] = {}

    def get(self, key: str, default: None = None) -> Instrument | None:
        return self.instruments.get(key, default)

    def __getitem__(self, symbol: str) -> Instrument:
        return self.instruments[symbol]

    def values(self):
        return self.instruments.values()

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
