from connector.connector import MarketType
from connector.gateio.gateio_base import GateioBase
from typing import Any


class GateioSpot(GateioBase):
    """
    Docs: https://www.gate.com/docs/developers/apiv4/en/#query-all-supported-currency-pairs
    """

    @property
    def market_type(self) -> MarketType:
        return MarketType.SPOT

    @property
    def exchange_info_url(self) -> str:
        return "spot/currency_pairs"

    @property
    def exchange_symbol_field(self) -> str:
        return "id"

    def _get_instruments_info_from_exchange_info(self, exchange_info: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return exchange_info

    @property
    def unified_symbol_fields(self) -> tuple[str, ...]:
        return ("base", "quote")

    @property
    def instrument_validation_dict(self) -> dict[str, Any]:
        return {
            "quote": "USDT",
            "trade_status": "tradable",
            "type": "normal",
        }
