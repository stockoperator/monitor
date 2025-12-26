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

    def _is_instrument_info_valid(self, inst_info: dict[str, Any]) -> bool:
        return inst_info["status"] == "Trading" and inst_info["contractType"] == "LinearPerpetual" and inst_info["quoteCoin"] == "USDT"
