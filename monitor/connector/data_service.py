from abc import ABC, abstractmethod
from logging import Logger
from typing import Type
from aiohttp import ClientSession, ClientWebSocketResponse
from asyncio import Queue, TaskGroup, sleep, CancelledError

from connector.async_logger import null_logger
from connector.data_parser import BaseDataParser
from connector.websocket import WebsocketManager
from connector.instrument import BaseInstrumentManager, InstrumentAddedEvent
from connector.events import Event
from connector.utils import traceback_error_str


class BaseDataService(ABC):
    def __init__(
        self,
        session: ClientSession,
        instruments: BaseInstrumentManager,
        logger: Logger = null_logger(),
    ) -> None:
        self.instruments = instruments
        self.logger = logger

        self.data_events: Queue[Event] = Queue()
        self.events: Queue[Event] = Queue()

        self.websocket_manager = WebsocketManager(session, self.ws_url, self.logger.getChild("ws"))
        self.data_parser = self.data_parser_type(self.websocket_manager, self.logger.getChild("data_parser"))

        self.instruments.on_change += self.events
        self.websocket_manager.on_connect += self.events
        self.data_parser.on_event += self.data_events

    @property
    @abstractmethod
    def ws_url(self) -> str: ...

    @property
    @abstractmethod
    def data_parser_type(self) -> Type[BaseDataParser]: ...

    async def event_loop(self, events: Queue[Event]):
        while True:
            event = await events.get()
            try:
                await self.handle_event(event)
            except CancelledError:
                raise
            except Exception:
                self.logger.error(traceback_error_str())
                await sleep(5)

    def get_channels(self, symbols: set[str]) -> list[str]:
        return [self.get_channel(s) for s in symbols]

    @abstractmethod
    def get_channel(self, symbol: str) -> str: ...

    @abstractmethod
    async def subscribe_channels(self, ws: ClientWebSocketResponse, channels: list[str], bytes_per_ws_message: int = 1000) -> None: ...

    async def subscribe_all(self) -> None:
        ws = self.websocket_manager.ws
        if isinstance(ws, ClientWebSocketResponse) and self.instruments.values():
            symbols = set(instrument.exchange_symbol for instrument in self.instruments.values())
            channels = self.get_channels(symbols)
            await self.subscribe_channels(ws, channels)

    async def subscribe(self, event: InstrumentAddedEvent) -> None:
        ws = self.websocket_manager.ws
        if isinstance(ws, ClientWebSocketResponse) and event.exchange_symbols:
            channels = self.get_channels(event.exchange_symbols)
            await self.subscribe_channels(ws, channels)

    @abstractmethod
    async def handle_event(self, event: Event) -> None: ...

    async def run(self) -> None:
        async with TaskGroup() as tg:
            tg.create_task(self.websocket_manager.loop())
            tg.create_task(self.data_parser.event_loop())
            tg.create_task(self.event_loop(self.data_events))
            tg.create_task(self.event_loop(self.events))
