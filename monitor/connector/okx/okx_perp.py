from connector.connector import MarketType, HTTPMethod
from connector.okx.okx_base import OkxBase
from typing import Any

BASE_URL = "https://www.okx.com/api/v5/"
EXCHANGE_INFO_URL = "public/instruments"


class OkxPerp(OkxBase):
    @property
    def market_type(self) -> MarketType:
        return MarketType.PERPETUAL

    async def _request_exchange_info(self) -> dict[str, Any]:
        params = {"instType": "SWAP"}
        return await self._request(HTTPMethod.GET, url=BASE_URL + EXCHANGE_INFO_URL, params=params)

    def _unify_symbol(self, instrument_info: dict[str, Any]) -> str:
        return f'{instrument_info["ctValCcy"]}{instrument_info["settleCcy"]}'.upper()

    def _is_instrument_info_valid(self, inst_info: dict[str, Any]) -> bool:
        return inst_info["ctType"] == "linear" and inst_info["state"] == "live" and inst_info["settleCcy"] == "USDT"
