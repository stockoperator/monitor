from connector.connector import AbstractConnector, ExchangeName
from typing import Any


class BitgetBase(AbstractConnector):
    @property
    def name(self) -> ExchangeName:
        return ExchangeName.BITGET

    @property
    def base_url(self) -> str:
        return "https://api.bitget.com/api/v2/"

    @property
    def exchange_symbol_field(self) -> str:
        return "symbol"

    def _get_instruments_info_from_exchange_info(self, exchange_info: dict[str, Any]) -> list[dict[str, Any]]:
        return exchange_info["data"]

    def _unify_symbol(self, instrument_info: dict[str, Any]) -> str:
        return f'{instrument_info["baseCoin"]}{instrument_info["quoteCoin"]}'.upper()
