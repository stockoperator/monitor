from connector.connector import MarketType
from connector.mexc.mexc_base import MexcBase
from typing import Any


class MexcPerp(MexcBase):
    """
    Docs: https://www.mexc.com/api-docs/futures/market-endpoints#get-contract-info
    """

    @property
    def market_type(self) -> MarketType:
        return MarketType.PERPETUAL

    @property
    def base_url(self) -> str:
        return "https://contract.mexc.com/api/"

    @property
    def exchange_info_url(self) -> str:
        return "v1/contract/detail"

    def _get_instruments_info_from_exchange_info(self, exchange_info: dict[str, Any]) -> list[dict[str, Any]]:
        return exchange_info["data"]

    @property
    def unified_symbol_fields(self) -> tuple[str, ...]:
        return ("baseCoin", "quoteCoin")

    @property
    def instrument_validation_dict(self) -> dict[str, Any]:
        # {"apiAllowed"] все выключены для api торговли
        return {
            "state": 0,
            "futureType": 1,
            "quoteCoin": "USDT",
        }
