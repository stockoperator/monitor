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

    @property
    def instrument_validation_dict(self) -> dict[str, Any]:
        return {
            "state": "live",
            "quoteCcy": "USDT",
        }
