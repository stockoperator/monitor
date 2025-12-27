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

    @property
    def instrument_validation_dict(self) -> dict[str, Any]:
        return {
            "isInverse": False,
            "status": "Open",
            "quoteCurrency": "USDT",
        }
