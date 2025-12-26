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

    def _is_instrument_info_valid(self, inst_info: dict[str, Any]) -> bool:
        return inst_info["status"] == "TRADING" and inst_info["contractType"] == "PERPETUAL" and inst_info["quoteAsset"] == "USDT"
