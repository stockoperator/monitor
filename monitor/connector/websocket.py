from aiohttp import ClientSession, ClientWebSocketResponse, WSMessage, WSMsgType
from logging import Logger
from asyncio import CancelledError, sleep

from connector.async_logger import null_logger
from connector.event_manager import EventManager
from connector.events import TextMessageEvent, WebsocketConnectedEvent
from connector.utils import traceback_error_str


class WebsocketManager:
    def __init__(
        self,
        session: ClientSession,
        url: str,
        logger: Logger = null_logger(),
        heartbeat: int = 20,
    ) -> None:
        self.session = session
        self.ws_url = url
        self.logger = logger
        self.heartbeat = heartbeat

        self.ws: ClientWebSocketResponse | None = None
        self.on_message = EventManager()
        self.on_connect = EventManager()

    def terminal_message(self, ws: ClientWebSocketResponse, msg: WSMessage) -> str:
        return (
            f"WebSocket terminal event. "
            f"msg_type: {msg.type.name}, "
            f"msg_data: {msg.data}, "
            f"msg_extra: {msg.extra}, "
            f"close_code: {ws.close_code}, "
            f"exception: {ws.exception()}"
        )

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

                    self.on_connect(WebsocketConnectedEvent())

                    while True:
                        msg = await ws.receive()
                        if msg.type == WSMsgType.TEXT:
                            self.on_message(TextMessageEvent(text=msg.data))
                        elif msg.type in (WSMsgType.CLOSED, WSMsgType.CLOSE, WSMsgType.CLOSING, WSMsgType.ERROR):
                            self.logger.error(f"{self.__class__.__name__} {self.terminal_message(ws, msg)}")
                            break
                        else:
                            self.logger.error(f"Unknown ws message type: {msg}")
            except CancelledError:
                raise
            except Exception:
                self.logger.error(traceback_error_str())
                await sleep(5)
