from connector.connector import MarketType, HTTPMethod
from connector.kukoin.kukoin_base import KukoinBase
from typing import Any

BASE_URL = "https://api.kucoin.com/api/"
EXCHANGE_INFO_URL = "v2/symbols"


class KukoinSpot(KukoinBase):
    @property
    def market_type(self) -> MarketType:
        return MarketType.SPOT

    async def _request_exchange_info(self) -> dict[str, Any]:
        """
        Docs: https://www.kucoin.com/docs-new/rest/spot-trading/market-data/get-all-symbols
        """
        return await self._request(HTTPMethod.GET, url=BASE_URL + EXCHANGE_INFO_URL)

    def _is_instrument_info_valid(self, inst_info: dict[str, Any]) -> bool:
        return inst_info["enableTrading"] is True and inst_info["quoteCurrency"] == "USDT"
