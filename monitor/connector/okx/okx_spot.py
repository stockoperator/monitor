from connector.connector import MarketType, HTTPMethod
from connector.okx.okx_base import OkxBase
from typing import Any

BASE_URL = "https://www.okx.com/api/v5/"
EXCHANGE_INFO_URL = "public/instruments"


class OkxSpot(OkxBase):
    @property
    def market_type(self) -> MarketType:
        return MarketType.SPOT

    async def _request_exchange_info(self) -> dict[str, Any]:
        params = {"instType": "SPOT"}
        return await self._request(HTTPMethod.GET, url=BASE_URL + EXCHANGE_INFO_URL, params=params)

    def _unify_symbol(self, instrument_info: dict[str, Any]) -> str:
        return f'{instrument_info["baseCcy"]}{instrument_info["quoteCcy"]}'.upper()

    def _is_instrument_info_valid(self, inst_info: dict[str, Any]) -> bool:
        return inst_info["state"] == "live" and inst_info["quoteCcy"] == "USDT"
