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

    def _is_instrument_info_valid(self, inst_info: dict[str, Any]) -> bool:
        return inst_info["status"] == "Trading" and inst_info["quoteCoin"] == "USDT"
