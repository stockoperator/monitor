import logging
from aiohttp import ClientWebSocketResponse
from abc import ABC, abstractmethod

from connector.async_logger import null_logger


class BaseSubscription(ABC):
    def __init__(
        self,
        logger: logging.Logger = null_logger(),
    ):
        self.logger = logger

    @abstractmethod
    def make_subscribe_message(self, channel_batch: list[str]) -> bytes: ...

    @abstractmethod
    async def subscribe_channels(self, ws: ClientWebSocketResponse, channels: list[str], bytes_per_ws_message: int = 1000) -> None: ...
