from connector.connector import MarketType
from connector.gateio.gateio_base import GateioBase
from typing import Any


class GateioPerp(GateioBase):
    """
    Docs: https://www.gate.com/docs/developers/apiv4/en/#query-all-futures-contracts
    """

    @property
    def market_type(self) -> MarketType:
        return MarketType.PERPETUAL

    @property
    def exchange_info_url(self) -> str:
        return "futures/usdt/contracts"

    @property
    def exchange_symbol_field(self) -> str:
        return "name"

    def _get_instruments_info_from_exchange_info(self, exchange_info: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return exchange_info

    def _unify_symbol(self, instrument_info: dict[str, Any]) -> str:
        return f'{instrument_info["name"]}'.replace("_", "").upper()

    @property
    def instrument_validation_dict(self) -> dict[str, Any]:
        return {
            "status": "trading",
            "type": "direct",
        }
