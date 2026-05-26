from enum import Enum
from typing import Callable, Awaitable
from aiohttp import ClientWebSocketResponse

WSSubscribeAllHandlerType = Callable[[ClientWebSocketResponse], Awaitable[None]]
InstrumentsAddedHandlerType = Callable[[set[str]], Awaitable[None]]
InstrumentsAddedHandlersType = set[InstrumentsAddedHandlerType]


class MarketType(Enum):
    SPOT = "spot"
    PERP = "perp"


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


class BaseOrderbook:
    def __init__(self):
        self.message: str = ""


class PartialOrderbook(BaseOrderbook):  # 20 ordered bids & acks for binance
    pass
