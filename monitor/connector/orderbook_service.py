from logging import Logger
from aiohttp import ClientSession
from collections import defaultdict
from abc import abstractmethod

from connector.async_logger import null_logger
from connector.base_classes import Orderbook, OrderbookDelta
from connector.instrument import BaseInstrumentManager
from connector.data_service import BaseDataService
from connector.events import Event, InstrumentAddedEvent, WebsocketConnectedEvent, OrderbookDeltaEvent


class BaseOrderbookService(BaseDataService):
    def __init__(
        self,
        session: ClientSession,
        instruments: BaseInstrumentManager,
        logger: Logger = null_logger(),
    ) -> None:
        self._items: dict[str, Orderbook] = defaultdict(Orderbook)
        super().__init__(
            session=session,
            instruments=instruments,
            logger=logger,
        )

    def __getitem__(self, symbol: str) -> Orderbook:
        return self._items[symbol]

    async def handle_event(self, event: Event) -> None:
        if isinstance(event, InstrumentAddedEvent):
            await self.subscribe(event)
        if isinstance(event, WebsocketConnectedEvent):
            for orderbook in self._items.values():
                orderbook.clear()
            await self.subscribe_all()
        if isinstance(event, OrderbookDeltaEvent):
            self.apply_delta(event.data)

    @abstractmethod
    def is_gap(self, delta: OrderbookDelta) -> bool: ...

    def apply_delta(self, delta: OrderbookDelta) -> None:
        orderbook: Orderbook = self._items[delta.symbol]

        if self.is_gap(delta):
            orderbook.clear()

        orderbook.last_id = delta.last_id
        orderbook.transaction_ts_ms = delta.transaction_ts_ms

        for level in delta.asks:
            if level.amount == 0.0:
                orderbook.asks.pop(level.price, None)  # type: ignore
            else:
                orderbook.asks[level.price] = level.amount

        for level in delta.bids:
            if level.amount == 0.0:
                orderbook.bids.pop(level.price, None)  # type: ignore
            else:
                orderbook.bids[level.price] = level.amount
