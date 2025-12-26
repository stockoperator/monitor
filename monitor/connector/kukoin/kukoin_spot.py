from connector.connector import MarketType
from connector.kukoin.kukoin_base import KukoinBase
from typing import Any


class KukoinSpot(KukoinBase):
    """
    Docs: https://www.kucoin.com/docs-new/rest/spot-trading/market-data/get-all-symbols
    """

    @property
    def market_type(self) -> MarketType:
        return MarketType.SPOT

    @property
    def base_url(self) -> str:
        return "https://api.kucoin.com/api/"

    @property
    def exchange_info_url(self) -> str:
        return "v2/symbols"

    def _is_instrument_info_valid(self, inst_info: dict[str, Any]) -> bool:
        return inst_info["enableTrading"] is True and inst_info["quoteCurrency"] == "USDT"
