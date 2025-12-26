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

    def _is_instrument_info_valid(self, inst_info: dict[str, Any]) -> bool:
        return inst_info["status"] == "online" and inst_info["quoteCoin"] == "USDT"
