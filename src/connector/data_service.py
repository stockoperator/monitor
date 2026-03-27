from abc import ABC, abstractmethod
from logging import Logger
from aiohttp import ClientSession, ClientWebSocketResponse
import asyncio


from connector.async_logger import null_logger
from connector.websocket import WebsocketTransport
from connector.instrument import BaseInstrumentManager
from connector.events import Event, WebsocketConnectedEvent, InstrumentAddedEvent
from connector.utils import traceback_error_str
from connector.subscription import BaseSubscription


class BaseDataService(ABC):
    def __init__(
        self,
        *,
        session: ClientSession,
        instruments: BaseInstrumentManager,
        logger: Logger = null_logger(),
    ) -> None:
        self.logger = logger

        self.event_queue: asyncio.Queue[Event] = asyncio.Queue()
        self.instruments = instruments
        self.instruments.on_instruments_added.add(self.event_queue)

        self.websocket_transport = WebsocketTransport(
            session=session,
            url=self.ws_url,
            logger=self.logger.getChild("ws"),
            message_handler=self.handle_message,
            event_queue=self.event_queue,
        )

        self.subscription = self.subscription_type(logger=self.logger.getChild("subscription"))

    @property
    @abstractmethod
    def ws_url(self) -> str: ...

    @abstractmethod
    def get_channel(self, symbol: str) -> str: ...

    @property
    @abstractmethod
    def subscription_type(self) -> type[BaseSubscription]: ...

    @abstractmethod
    def handle_message(self, message: str) -> None: ...

    def get_channels(self, symbols: set[str]) -> list[str]:
        return [self.get_channel(s) for s in symbols]

    async def subscribe_all(self, ws: ClientWebSocketResponse) -> None:
        if self.instruments.values():
            symbols = set(instrument.exchange_symbol for instrument in self.instruments.values())
            channels = self.get_channels(symbols)
            await self.subscription.subscribe_channels(ws, channels)

    async def subscribe(self, instruments: set[str]) -> None:
        ws = self.websocket_transport.ws
        if instruments and isinstance(ws, ClientWebSocketResponse) and not ws.closed:
            channels = self.get_channels(instruments)
            await self.subscription.subscribe_channels(ws, channels)

    async def handle_event(self, event: Event) -> None:
        if isinstance(event, WebsocketConnectedEvent):
            await self.subscribe_all(event.ws)
        if isinstance(event, InstrumentAddedEvent):
            ws = self.websocket_transport.ws
            if ws and not ws.closed:
                channels = self.get_channels(event.symbols)
                await self.subscription.subscribe_channels(ws, channels)

    async def event_loop(self):
        while True:
            event = await self.event_queue.get()
            try:
                await self.handle_event(event)
            except asyncio.CancelledError:
                raise
            except Exception:
                self.logger.error(traceback_error_str())
                await asyncio.sleep(5)

    async def run(self) -> None:
        async with asyncio.TaskGroup() as tg:
            tg.create_task(self.websocket_transport.loop())
            tg.create_task(self.event_loop())
