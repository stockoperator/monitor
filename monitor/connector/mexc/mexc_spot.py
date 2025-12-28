from connector.connector import MarketType
from connector.mexc.mexc_base import MexcBase
from typing import Any


class MexcSpot(MexcBase):
    """
    Docs: https://www.mexc.com/api-docs/spot-v3/market-data-endpoints#exchange-information
    """

    @property
    def market_type(self) -> MarketType:
        return MarketType.SPOT

    @property
    def base_url(self) -> str:
        return "https://api.mexc.com/api/"

    @property
    def exchange_info_url(self) -> str:
        return "v3/exchangeInfo"

    def _get_instruments_info_from_exchange_info(self, exchange_info: dict[str, Any]) -> list[dict[str, Any]]:
        return exchange_info["symbols"]

    @property
    def unified_symbol_fields(self) -> tuple[str, ...]:
        return ("baseAsset", "quoteAsset")

    @property
    def instrument_validation_dict(self) -> dict[str, Any]:
        return {
            "status": "1",
            "quoteAsset": "USDT",
        }
