from enum import Enum
from dataclasses import dataclass, field
from sortedcontainers import SortedDict  # type: ignore[import-untyped]


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


@dataclass(slots=True, frozen=True)
class PriceLevel:
    price: float
    amount: float


@dataclass(slots=True, frozen=True)
class OrderbookDelta:
    symbol: str
    exchange_ts_ms: int
    transaction_ts_ms: int
    first_id: int
    last_id: int
    prev_last_id: int
    bids: list[PriceLevel]
    asks: list[PriceLevel]


@dataclass(slots=True, frozen=True)
class PublicTrade:
    symbol: str
    exchange_ts_ms: int
    transaction_ts_ms: int
    trade_id: str
    price: float
    amount: float
    buy: bool


@dataclass(kw_only=True, eq=False, slots=True)
class Orderbook:
    last_id: int = field(init=False, default=0)
    transaction_ts_ms: int = field(init=False, default=0)
    asks: SortedDict[float, float] = field(init=False, default_factory=lambda: SortedDict())  # type: ignore
    bids: SortedDict[float, float] = field(init=False, default_factory=lambda: SortedDict())  # type: ignore

    @property
    def best_ask(self) -> float:
        return self.asks.peekitem(0)[0] if self.asks else float("inf")  # type: ignore

    @property
    def best_bid(self) -> float:
        return self.bids.peekitem(-1)[0] if self.bids else 0.0  # type: ignore

    def clear(self):
        self.asks.clear()
        self.bids.clear()
        self.last_id = 0
