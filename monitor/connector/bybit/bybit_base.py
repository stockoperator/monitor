from connector.connector import AbstractConnector, ExchangeName
from typing import Any


class BybitBase(AbstractConnector):
    @property
    def name(self) -> ExchangeName:
        return ExchangeName.BYBIT

    @property
    def base_url(self) -> str:
        return "https://api.bybit.com/v5/"

    @property
    def exchange_symbol_field(self) -> str:
        return "symbol"

    def _unify_symbol(self, instrument_info: dict[str, Any]) -> str:
        return f'{instrument_info["baseCoin"]}{instrument_info["quoteCoin"]}'.upper()

    def _get_instruments_info_from_exchange_info(self, exchange_info: dict[str, Any]) -> list[dict[str, Any]]:
        return exchange_info["result"]["list"]
