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

    def _is_instrument_info_valid(self, inst_info: dict[str, Any]) -> bool:
        return inst_info["status"] == "TRADING" and inst_info["quoteAsset"] == "USDT"
