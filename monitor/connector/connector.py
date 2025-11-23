from abc import ABC, abstractmethod
from typing import Any
from enum import Enum
from dataclasses import dataclass, field
import aiohttp
import asyncio
from connector.utils import traceback_error_str

MINUTE = 60  # Secs
INSTRUMENT_INTERVAL = 30 * MINUTE


class HTTPMethod(Enum):
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    DELETE = "DELETE"


class MarketType(Enum):
    SPOT = "spot"
    PERPETUAL = "perpetual"


class ExchangeName(Enum):
    BINANCE = "binance"
    MEXC = "mexc"
    GATEIO = "gateio"
    BITGET = "bitget"
    KUCOIN = "kucoin"
    BYBIT = "bybit"
    OKX = "okx"
    COINBASE = "coinbase"
    BITFINEX = "bitfinex"
    KRAKEN = "kraken"
    BITSTAMP = "bitstamp"
    HTX = "htx"


@dataclass(kw_only=True, eq=False, slots=True)
class Instrument:
    exchange: ExchangeName
    market_type: MarketType
    exchange_symbol: str  # биржевое имя: "BTC-USDT или BTC_USDT"
    unified_symbol: str  # унифицированное: "BTCUSDT"
    min_price: float | None = None
    max_price: float | None = None
    price_step: float | None = None
    min_qty: float | None = None
    max_qty: float | None = None
    qty_step: float | None = None


@dataclass(kw_only=True, eq=False, slots=True)
class AbstractConnector(ABC):
    session: aiohttp.ClientSession
    api_key: str = ""
    secret_key: str = ""
    passphrase: str = ""
    instruments: dict[str, Instrument] = field(init=False, default_factory=lambda: {})

    @property
    @abstractmethod
    def name(self) -> ExchangeName:
        """Logical name of the exchange, e.g., 'binance'."""
        ...

    @property
    @abstractmethod
    def market_type(self) -> MarketType:
        """Market type: SPOT, PERPETUAL, etc."""
        ...

    @abstractmethod
    def _sign(self, message: str) -> str:
        """Method for signing the request."""
        ...

    @abstractmethod
    async def _request(self, method: HTTPMethod, url: str, params: dict[str, Any] | None = None, is_auth_required: bool = False) -> dict[str, Any]:
        """Sending requests to the exchange's API."""
        ...

    @abstractmethod
    async def _request_exchange_info(self) -> dict[str, Any]: ...

    @abstractmethod
    def _get_instruments_info_from_exchange_info(self, exchange_info: dict[str, Any]) -> list[dict[str, Any]]: ...

    @abstractmethod
    def _unify_symbol(self, instrument_info: dict[str, Any]) -> str: ...

    @abstractmethod
    def _make_instrument_from_instrument_info(self, instrument_info: dict[str, Any]) -> Instrument: ...

    @abstractmethod
    def _is_instrument_info_valid(self, inst_info: dict[str, Any]) -> bool: ...

    def _make_instruments_from_exchange_info(self, exchange_info: dict[str, Any]) -> list[Instrument]:
        instruments: list[Instrument] = []
        for instrument_info in self._get_instruments_info_from_exchange_info(exchange_info):
            if self._is_instrument_info_valid(instrument_info):
                instruments.append(self._make_instrument_from_instrument_info(instrument_info))
        return instruments

    async def _update_instruments(self) -> None:
        exchange_info = await self._request_exchange_info()
        for instrument in self._make_instruments_from_exchange_info(exchange_info):
            self.instruments[instrument.unified_symbol] = instrument

    async def _update_instruments_loop(self):
        """
        Updates the instruments by requesting the latest definitions from the exchange.
        Executes regularly every 30 minutes
        """
        while True:
            try:
                await self._update_instruments()
                await asyncio.sleep(INSTRUMENT_INTERVAL)
            except NotImplementedError:
                raise
            except asyncio.CancelledError:
                raise
            except Exception as e:
                ...  # self.logger()
                print(traceback_error_str())
                print(e.__repr__())
                await asyncio.sleep(0.5)

    async def start_tasks(self):
        asyncio.create_task(self._update_instruments_loop())
