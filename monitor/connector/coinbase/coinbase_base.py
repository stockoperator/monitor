from abc import ABC, abstractmethod
from connector.connector import AbstractConnector, Instrument, ExchangeName, MarketType, HTTPMethod
from typing import Any
import hmac

BASE_URL = "https://api.international.coinbase.com/api/"
EXCHANGE_INFO_URL = "v1/instruments"


class CoinbaseBase(AbstractConnector, ABC):
    """
    Docs: https://docs.cdp.coinbase.com/api-reference/international-exchange-api/rest-api/instruments/list-instruments
    """

    @property
    def name(self) -> ExchangeName:
        return ExchangeName.COINBASE

    @property
    @abstractmethod
    def market_type(self) -> MarketType: ...

    def _sign(self, message: str) -> str:
        return hmac.new(key=self.secret_key.encode("utf-8"), msg=message.encode("utf-8"), digestmod="sha256").hexdigest()

    async def _request(self, method: HTTPMethod, url: str, params: dict[str, Any] | None = None, is_auth_required: bool = False) -> dict[str, Any]:
        params = params if params else {}
        headers: dict[str, Any] = {}

        if is_auth_required:
            pass

        async with self.session.request(method=method.value, url=url, params=params, headers=headers) as response:
            return await response.json()

    async def _request_exchange_info(self) -> dict[str, Any]:
        """
        Docs: https://docs.cdp.coinbase.com/api-reference/international-exchange-api/rest-api/instruments/list-instruments
        """
        exchange_info = await self._request(HTTPMethod.GET, url=BASE_URL + EXCHANGE_INFO_URL)
        return {"data": exchange_info}

    def _get_instruments_info_from_exchange_info(self, exchange_info: dict[str, Any]) -> list[dict[str, Any]]:
        return exchange_info["data"]

    def _unify_symbol(self, instrument_info: dict[str, Any]) -> str:
        return f'{instrument_info["base_asset_name"]}{instrument_info["quote_asset_name"]}'.upper()

    @abstractmethod
    def _is_instrument_info_valid(self, inst_info: dict[str, Any]) -> bool: ...

    def _make_instrument_from_instrument_info(self, instrument_info: dict[str, Any]) -> Instrument:
        instrument = Instrument(
            exchange=self.name,
            market_type=self.market_type,
            exchange_symbol=instrument_info["symbol"],
            unified_symbol=self._unify_symbol(instrument_info),
        )
        return instrument
