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

    @property
    def unified_symbol_fields(self) -> tuple[str, ...]:
        return ("baseCcy", "quoteCcy")

    @property
    def instrument_validation_dict(self) -> dict[str, Any]:
        return {
            "state": "live",
            "quoteCcy": "USDT",
        }
