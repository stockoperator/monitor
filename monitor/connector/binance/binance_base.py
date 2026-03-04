import hmac
import time
from typing import Any

from connector.connector import BaseConnector
from connector.base_classes import ExchangeName
from connector.http_client import BaseHttpClient, HTTPMethod
from connector.instrument import BaseInstrumentManager


class BinanceHttpClientBase(BaseHttpClient):
    def _sign(self, message: str) -> str:
        return hmac.new(key=self.secret_key.encode("utf-8"), msg=message.encode("utf-8"), digestmod="sha256").hexdigest()

    async def request(self, method: HTTPMethod, url: str, params: dict[str, Any] | None = None, is_auth_required: bool = False) -> dict[str, Any]:
        params = params if params else {}
        headers = {}

        if is_auth_required:
            headers = {"X-MBX-APIKEY": self.api_key}
            params["timestamp"] = int((time.time() - 10) * 1000)
            params["recvWindow"] = 50000

            query_str = "&".join(f"{k}={v}" for k, v in params.items())
            params["signature"] = self._sign(query_str)

        async with self.session.request(method=method.value, url=url, params=params, headers=headers) as response:
            return await response.json()


class BinanceBaseInstrumentManager(BaseInstrumentManager):
    def instruments_info(self, exchange_info: Any) -> list[dict[str, Any]]:
        return exchange_info["symbols"]


class BinanceBase(BaseConnector):
    @property
    def name(self) -> ExchangeName:
        return ExchangeName.BINANCE
