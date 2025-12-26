from connector.connector import MarketType
from connector.okx.okx_base import OkxBase
from typing import Any


class OkxPerp(OkxBase):
    @property
    def market_type(self) -> MarketType:
        return MarketType.PERPETUAL

    @property
    def exchange_info_url(self) -> str:
        return "public/instruments?instType=SWAP"

    def _unify_symbol(self, instrument_info: dict[str, Any]) -> str:
        return f'{instrument_info["ctValCcy"]}{instrument_info["settleCcy"]}'.upper()

    def _is_instrument_info_valid(self, inst_info: dict[str, Any]) -> bool:
        return inst_info["ctType"] == "linear" and inst_info["state"] == "live" and inst_info["settleCcy"] == "USDT"
