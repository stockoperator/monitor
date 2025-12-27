from connector.connector import MarketType
from connector.binance.binance_base import BinanceBase
from typing import Any


class BinanceSpot(BinanceBase):
    @property
    def market_type(self) -> MarketType:
        return MarketType.SPOT

    @property
    def base_url(self) -> str:
        return "https://api.binance.com/api/"

    @property
    def exchange_info_url(self) -> str:
        return "v3/exchangeInfo"

    @property
    def instrument_validation_dict(self) -> dict[str, Any]:
        return {
            "status": "TRADING",
            "quoteAsset": "USDT",
        }
