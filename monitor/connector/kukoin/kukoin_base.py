from connector.connector import AbstractConnector, ExchangeName
from typing import Any


class KukoinBase(AbstractConnector):
    """
    Docs: https://www.kucoin.com/docs-new
    """

    @property
    def name(self) -> ExchangeName:
        return ExchangeName.KUCOIN

    @property
    def exchange_symbol_field(self) -> str:
        return "symbol"

    def _get_instruments_info_from_exchange_info(self, exchange_info: dict[str, Any]) -> list[dict[str, Any]]:
        return exchange_info["data"]

    def _unify_symbol(self, instrument_info: dict[str, Any]) -> str:
        return f'{instrument_info["baseCurrency"]}{instrument_info["quoteCurrency"]}'.upper()
