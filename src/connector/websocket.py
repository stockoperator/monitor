from aiohttp import ClientSession, ClientWebSocketResponse, WSMessage, WSMsgType
from logging import Logger
from asyncio import CancelledError, sleep
from typing import Callable
from asyncio import Queue

from connector.async_logger import null_logger
from connector.utils import traceback_error_str
from connector.event_queue_manager import EventQueueManager
from connector.events import Event, WebsocketConnectedEvent


class WebsocketTransport:
    def __init__(
        self,
        *,
        session: ClientSession,
        url: str,
        message_handler: Callable[[str], None],
        logger: Logger = null_logger(),
        event_queue: Queue[Event] | None = None,
        heartbeat: int = 20,
    ) -> None:
        self.session = session
        self.ws_url = url
        self.logger = logger
        self.heartbeat = heartbeat
        self.message_handler = message_handler

        self.on_connected: EventQueueManager = EventQueueManager()
        if event_queue:
            self.on_connected += event_queue
        self.ws: ClientWebSocketResponse | None = None

    def terminal_message(self, ws: ClientWebSocketResponse, msg: WSMessage) -> str:
        return f"terminal message. type: {msg.type.name}, data: {msg.data}, extra: {msg.extra}, exception: {ws.exception()}"

    async def loop(self) -> None:
        while True:
            try:
                async with self.session.ws_connect(self.ws_url, heartbeat=self.heartbeat) as ws:
                    self.ws = ws
                    try:
                        peer_ip = ws._writer.transport.get_extra_info("socket").getpeername()[0]  # pyright: ignore[reportPrivateUsage]
                        self.logger.info(f"{peer_ip} connected.")
                    except Exception:
                        self.logger.error(traceback_error_str())

                    self.on_connected(WebsocketConnectedEvent(ws))

                    count: int = 0
                    while True:
                        msg = await ws.receive()
                        if msg.type == WSMsgType.TEXT:
                            self.message_handler(msg.data)
                            count += 1
                            if count % 100 == 0:
                                await sleep(0)
                                count = 0
                        elif msg.type in (WSMsgType.CLOSED, WSMsgType.CLOSE, WSMsgType.CLOSING, WSMsgType.ERROR):
                            self.logger.error(self.terminal_message(ws, msg))
                            break
                        else:
                            self.logger.error(f"Unknown ws message type: {msg}")
            except CancelledError:
                raise
            except Exception:
                self.logger.error(traceback_error_str())
                await sleep(5)
