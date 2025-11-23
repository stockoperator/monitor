from abc import ABC, abstractmethod
from connector.connector import AbstractConnector, Instrument, ExchangeName, MarketType, HTTPMethod
from typing import Any
import hmac
import time


class BinanceBase(AbstractConnector, ABC):
    @property
    def name(self) -> ExchangeName:
        return ExchangeName.BINANCE

    @property
    @abstractmethod
    def market_type(self) -> MarketType: ...

    def _sign(self, message: str) -> str:
        return hmac.new(key=self.secret_key.encode("utf-8"), msg=message.encode("utf-8"), digestmod="sha256").hexdigest()

    async def _request(self, method: HTTPMethod, url: str, params: dict[str, Any] | None = None, is_auth_required: bool = False) -> dict[str, Any]:
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

    def _unify_symbol(self, instrument_info: dict[str, Any]) -> str:
        return f'{instrument_info["baseAsset"]}{instrument_info["quoteAsset"]}'.upper()

    @abstractmethod
    async def _request_exchange_info(self) -> dict[str, Any]: ...

    def _get_instruments_info_from_exchange_info(self, exchange_info: dict[str, Any]) -> list[dict[str, Any]]:
        return exchange_info["symbols"]

    @abstractmethod
    def _is_instrument_info_valid(self, inst_info: dict[str, Any]) -> bool: ...

    @abstractmethod
    def _make_instrument_from_instrument_info(self, instrument_info: dict[str, Any]) -> Instrument: ...
