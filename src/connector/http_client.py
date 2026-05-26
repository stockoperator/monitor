from abc import ABC, abstractmethod
from typing import Any, Mapping
from enum import Enum
from aiohttp import ClientSession, ClientTimeout
import logging

from connector.async_logger import null_logger


class HTTPMethod(Enum):
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    DELETE = "DELETE"


class HttpResponse:
    __slots__ = ("data", "status", "headers")

    def __init__(self, data: Any, status: int, headers: Mapping[str, str]):
        self.data = data
        self.status = status
        self.headers = headers


def make_session(*, total_timeout: float = 30.0) -> ClientSession:
    timeout = ClientTimeout(total=total_timeout)
    return ClientSession(timeout=timeout)


class BaseHttpClient(ABC):
    def __init__(
        self,
        *,
        session: ClientSession,
        api_key: str = "",
        secret_key: str = "",
        passphrase: str = "",
        logger: logging.Logger = null_logger(),
    ) -> None:
        self.session = session
        self.api_key = api_key
        self.secret_key = secret_key
        self.passphrase = passphrase
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
    ) -> HttpResponse: ...
