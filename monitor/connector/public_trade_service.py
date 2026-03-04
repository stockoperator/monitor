from logging import Logger
from aiohttp import ClientSession
from collections import deque
from collections import defaultdict

from connector.async_logger import null_logger
from connector.base_classes import PublicTrade
from connector.instrument import BaseInstrumentManager
from connector.data_service import BaseDataService
from connector.events import Event, InstrumentAddedEvent, WebsocketConnectedEvent, PublicTradeEvent


class BasePublicTradeService(BaseDataService):
    def __init__(
        self,
        session: ClientSession,
        instruments: BaseInstrumentManager,
        logger: Logger = null_logger(),
    ) -> None:
        self._items: dict[str, deque[PublicTrade]] = defaultdict(lambda: deque(maxlen=10_000))
        super().__init__(
            session=session,
            instruments=instruments,
            logger=logger,
        )

    def __getitem__(self, symbol: str) -> deque[PublicTrade]:
        return self._items[symbol]

    def add_public_trade(self, public_trade: PublicTrade) -> None:
        public_trades = self._items[public_trade.symbol]
        public_trades.append(public_trade)

    async def handle_event(self, event: Event) -> None:
        if isinstance(event, InstrumentAddedEvent):
            await self.subscribe(event)
        if isinstance(event, WebsocketConnectedEvent):
            await self.subscribe_all()
        if isinstance(event, PublicTradeEvent):
            self.add_public_trade(event.data)
