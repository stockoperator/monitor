from dataclasses import dataclass
from aiohttp import ClientWebSocketResponse

from connector.trading_types import Order


class Event:
    pass


@dataclass(slots=True, frozen=True)
class InstrumentAddedEvent(Event):
    symbols: set[str]  # exchange_symbols


@dataclass(slots=True, frozen=True)
class WebsocketConnectedEvent(Event):
    ws: ClientWebSocketResponse


@dataclass(slots=True, frozen=True)
class OrderUpdateEvent(Event):
    order: Order
