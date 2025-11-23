from connector.connector import MarketType, HTTPMethod, Instrument
from connector.mexc.mexc_base import MexcBase
from typing import Any

BASE_URL = "https://api.mexc.com/api/"
EXCHANGE_INFO_URL = "v3/exchangeInfo"


class MexcSpot(MexcBase):
    @property
    def market_type(self) -> MarketType:
        return MarketType.SPOT

    async def _request_exchange_info(self) -> dict[str, Any]:
        """
        Docs: https://www.mexc.com/api-docs/spot-v3/market-data-endpoints#exchange-information
        """
        return await self._request(HTTPMethod.GET, url=BASE_URL + EXCHANGE_INFO_URL)

    def _get_instruments_info_from_exchange_info(self, exchange_info: dict[str, Any]) -> list[dict[str, Any]]:
        return exchange_info["symbols"]

    def _unify_symbol(self, instrument_info: dict[str, Any]) -> str:
        return f'{instrument_info["baseAsset"]}{instrument_info["quoteAsset"]}'.upper()

    def _is_instrument_info_valid(self, inst_info: dict[str, Any]) -> bool:
        return inst_info["status"] == "1" and inst_info["quoteAsset"] == "USDT"

    def _make_instrument_from_instrument_info(self, instrument_info: dict[str, Any]) -> Instrument:
        instrument = Instrument(
            exchange=self.name,
            market_type=self.market_type,
            exchange_symbol=instrument_info["symbol"],
            unified_symbol=self._unify_symbol(instrument_info),
        )
        return instrument
