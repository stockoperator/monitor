from connector.connector import MarketType
from connector.bitget.bitget_base import BitgetBase
from typing import Any


class BitgetSpot(BitgetBase):
    @property
    def market_type(self) -> MarketType:
        return MarketType.SPOT

    @property
    def exchange_info_url(self) -> str:
        return "spot/public/symbols"

    @property
    def instrument_validation_dict(self) -> dict[str, Any]:
        return {
            "status": "online",
            "quoteCoin": "USDT",
        }
