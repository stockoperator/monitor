from abc import ABC, abstractmethod
import orjson
from logging import Logger
from asyncio import Queue, sleep, CancelledError
from typing import Any

from connector.async_logger import null_logger
from connector.event_manager import EventManager
from connector.websocket import WebsocketManager
from connector.events import TextMessageEvent
from connector.utils import traceback_error_str


class BaseDataParser(ABC):
    def __init__(
        self,
        websocket_manager: WebsocketManager,
        logger: Logger = null_logger(),
    ) -> None:
        self.logger = logger

        self.events: Queue[TextMessageEvent] = Queue()
        websocket_manager.on_message += self.events
        self.on_event = EventManager()

    async def event_loop(self):
        while True:
            event = await self.events.get()
            try:
                data: dict[str, Any] = orjson.loads(event.text)
                await self.route_message(data)
            except CancelledError:
                raise
            except Exception:
                self.logger.error(traceback_error_str())
                await sleep(5)

    @abstractmethod
    async def route_message(self, data: dict[str, Any]) -> None: ...
