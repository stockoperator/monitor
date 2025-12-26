from connector.connector import MarketType
from connector.kukoin.kukoin_base import KukoinBase
from typing import Any


class KukoinPerp(KukoinBase):
    """
    Docs: https://www.kucoin.com/docs-new/rest/futures-trading/market-data/get-all-symbols
    """

    @property
    def market_type(self) -> MarketType:
        return MarketType.PERPETUAL

    @property
    def base_url(self) -> str:
        return "https://api-futures.kucoin.com/api/"

    @property
    def exchange_info_url(self) -> str:
        return "v1/contracts/active"

    def _is_instrument_info_valid(self, inst_info: dict[str, Any]) -> bool:
        return inst_info["isInverse"] is False and inst_info["status"] == "Open" and inst_info["quoteCurrency"] == "USDT"
