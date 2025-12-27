from connector.connector import MarketType
from connector.bybit.bybit_base import BybitBase
from typing import Any


class BybitPerp(BybitBase):
    @property
    def market_type(self) -> MarketType:
        return MarketType.PERPETUAL

    @property
    def exchange_info_url(self) -> str:
        return "market/instruments-info?category=linear"

    @property
    def instrument_validation_dict(self) -> dict[str, Any]:
        return {
            "status": "Trading",
            "contractType": "LinearPerpetual",
            "quoteCoin": "USDT",
        }
