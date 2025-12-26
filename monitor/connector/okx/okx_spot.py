from connector.connector import MarketType
from connector.okx.okx_base import OkxBase
from typing import Any


class OkxSpot(OkxBase):
    @property
    def market_type(self) -> MarketType:
        return MarketType.SPOT

    @property
    def exchange_info_url(self) -> str:
        return "public/instruments?instType=SPOT"

    def _unify_symbol(self, instrument_info: dict[str, Any]) -> str:
        return f'{instrument_info["baseCcy"]}{instrument_info["quoteCcy"]}'.upper()

    def _is_instrument_info_valid(self, inst_info: dict[str, Any]) -> bool:
        return inst_info["state"] == "live" and inst_info["quoteCcy"] == "USDT"
