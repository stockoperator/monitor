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

    @property
    def instrument_validation_dict(self) -> dict[str, Any]:
        return {
            "ctType": "linear",
            "state": "live",
            "settleCcy": "USDT",
        }
