from abc import ABC, abstractmethod
from logging import Logger
from aiohttp import ClientSession
import asyncio
import orjson


from connector.async_logger import null_logger
from connector.rate_limiter import BaseRateLimiterHttpClient
from connector.websocket import WebsocketTransport
from connector.instrument import BaseInstrumentManager
from connector.events import Event, WebsocketConnectedEvent, InstrumentAddedEvent
from connector.utils import traceback_error_str


class BaseDataService(ABC):
    def __init__(
        self,
        *,
        session: ClientSession,
        http_client: BaseRateLimiterHttpClient,
        instrument_manager: BaseInstrumentManager,
        logger: Logger = null_logger(),
        bytes_per_ws_message: int = 1000,
    ) -> None:
        self.logger = logger
        self.http_client = http_client
        self.bytes_per_ws_message = bytes_per_ws_message

        self.incoming_events: asyncio.Queue[Event] = asyncio.Queue()
        self.instrument_manager = instrument_manager
        self.instrument_manager.subscribers.add(self.incoming_events)

        self.websocket_transport = WebsocketTransport(
            session=session,
            url=self.ws_url,
            logger=self.logger.getChild("ws"),
            on_message=self.handle_message,
            on_connected=lambda ws: self.incoming_events.put_nowait(WebsocketConnectedEvent(ws)),
        )

    @property
    @abstractmethod
    def ws_url(self) -> str: ...

    @abstractmethod
    def make_subscribe_message(self, channel_batch: list[str]) -> bytes: ...

    @abstractmethod
    def get_channel(self, symbol: str) -> str: ...

    @abstractmethod
    def handle_message(self, message: str) -> None: ...

    async def handle_instruments_added(self, symbols: set[str]) -> None: ...

    def get_channels(self, symbols: set[str]) -> list[str]:
        return [self.get_channel(s) for s in symbols]

    async def subscribe_channels(self, channels: list[str]) -> None:
        ws = self.websocket_transport.ws
        if ws and not ws.closed and channels:
            channel_len = len(orjson.dumps(channels[0])) + 1
            non_channel_len = len(self.make_subscribe_message(channels[0:1])) - channel_len + 1
            batch_size = int(0.9 * (self.bytes_per_ws_message - non_channel_len) // channel_len)

            start_id: int = 0

            while start_id < len(channels):
                end_id: int = min(len(channels), start_id + batch_size)  # end_id not included!
                if start_id >= end_id:
                    raise ValueError("start_id >= end_id")
                message = self.make_subscribe_message(channels[start_id:end_id])
                if len(message) > self.bytes_per_ws_message:
                    batch_size -= 1
                else:
                    await asyncio.sleep(1)  # limits
                    if ws.closed:
                        break
                    await ws.send_str(message.decode("utf-8"))
                    start_id = end_id
            self.logger.info("subscribe all finished")

    async def subscribe_all(self) -> None:
        if self.instrument_manager.values():
            symbols = set(instrument.exchange_symbol for instrument in self.instrument_manager.values())
            channels = self.get_channels(symbols)
            await self.subscribe_channels(channels)

    async def subscribe(self, instruments: set[str]) -> None:
        if instruments:
            channels = self.get_channels(instruments)
            await self.subscribe_channels(channels)

    async def handle_event(self, event: Event) -> None:
        if isinstance(event, WebsocketConnectedEvent):
            await self.subscribe_all()

        if isinstance(event, InstrumentAddedEvent):
            await self.subscribe(event.symbols)
            await self.handle_instruments_added(event.symbols)

    async def imcoming_event_loop(self):
        while True:
            event = await self.incoming_events.get()
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
            tg.create_task(self.imcoming_event_loop())
