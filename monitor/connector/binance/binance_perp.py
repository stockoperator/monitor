from connector.connector import MarketType
from connector.binance.binance_base import BinanceBase
from typing import Any


class BinancePerp(BinanceBase):
    @property
    def market_type(self) -> MarketType:
        return MarketType.PERPETUAL

    @property
    def base_url(self) -> str:
        return "https://fapi.binance.com/fapi/"

    @property
    def exchange_info_url(self) -> str:
        return "v1/exchangeInfo"

    @property
    def instrument_validation_dict(self) -> dict[str, Any]:
        return {
            "status": "TRADING",
            "contractType": "PERPETUAL",
            "quoteAsset": "USDT",
        }
