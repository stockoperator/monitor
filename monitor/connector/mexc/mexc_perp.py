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

    def _unify_symbol(self, instrument_info: dict[str, Any]) -> str:
        return f'{instrument_info["baseCoin"]}{instrument_info["quoteCoin"]}'.upper()

    def _is_instrument_info_valid(self, inst_info: dict[str, Any]) -> bool:
        # inst_info["apiAllowed"] все выключены для api торговли
        return inst_info["state"] == 0 and inst_info["futureType"] == 1 and inst_info["quoteCoin"] == "USDT"
