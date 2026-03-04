from abc import ABC, abstractmethod
from typing import Any
from enum import Enum
from aiohttp import ClientSession, TCPConnector, ClientTimeout
import logging

from connector.async_logger import null_logger


class HTTPMethod(Enum):
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    DELETE = "DELETE"


def make_session(*, total_timeout: float = 10.0, limit_per_host: int = 10) -> ClientSession:
    connector = TCPConnector(keepalive_timeout=30, limit_per_host=limit_per_host, ttl_dns_cache=300)
    timeout = ClientTimeout(total=total_timeout)
    return ClientSession(connector=connector, timeout=timeout)


class BaseHttpClient(ABC):
    def __init__(
        self,
        session: ClientSession,
        api_key: str = "",
        secret_key: str = "",
        logger: logging.Logger = null_logger(),
    ) -> None:
        self.session = session
        self.api_key = api_key
        self.secret_key = secret_key
        self.logger = logger

    @abstractmethod
    def _sign(self, message: str) -> str: ...

    @abstractmethod
    async def request(
        self,
        method: HTTPMethod,
        url: str,
        params: dict[str, Any] | None = None,
        is_auth_required: bool = False,
    ) -> dict[str, Any]: ...
