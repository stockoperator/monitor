from connector.connector import MarketType
from connector.bitget.bitget_base import BitgetBase
from typing import Any


class BitgetPerp(BitgetBase):
    @property
    def market_type(self) -> MarketType:
        return MarketType.PERPETUAL

    @property
    def exchange_info_url(self) -> str:
        return "mix/market/contracts?productType=USDT-FUTURES"

    def _is_instrument_info_valid(self, inst_info: dict[str, Any]) -> bool:
        return inst_info["symbolType"] == "perpetual" and inst_info["symbolStatus"] == "normal"
