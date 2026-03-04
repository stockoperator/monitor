from dataclasses import dataclass
from connector.base_classes import OrderbookDelta, PublicTrade


class Event:
    pass


@dataclass(slots=True, frozen=True)
class InstrumentAddedEvent(Event):
    exchange_symbols: set[str]


@dataclass(slots=True, frozen=True)
class InstrumentRemovedEvent(Event):
    exchange_symbols: set[str]


@dataclass(slots=True, frozen=True)
class TextMessageEvent(Event):
    text: str


@dataclass(slots=True, frozen=True)
class WebsocketConnectedEvent(Event):
    pass


@dataclass(slots=True, frozen=True)
class OrderbookDeltaEvent(Event):
    data: OrderbookDelta


@dataclass(slots=True, frozen=True)
class PublicTradeEvent(Event):
    data: PublicTrade
