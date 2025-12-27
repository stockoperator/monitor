from connector.connector import MarketType
from connector.bybit.bybit_base import BybitBase
from typing import Any


class BybitSpot(BybitBase):
    @property
    def market_type(self) -> MarketType:
        return MarketType.SPOT

    @property
    def exchange_info_url(self) -> str:
        return "market/instruments-info?category=spot"

    @property
    def instrument_validation_dict(self) -> dict[str, Any]:
        return {
            "status": "Trading",
            "quoteCoin": "USDT",
        }
