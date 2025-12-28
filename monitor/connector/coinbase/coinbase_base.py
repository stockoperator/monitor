from connector.connector import AbstractConnector, ExchangeName
from typing import Any


class CoinbaseBase(AbstractConnector):
    """
    Docs: https://docs.cdp.coinbase.com/api-reference/international-exchange-api/rest-api/instruments/list-instruments
    """

    @property
    def name(self) -> ExchangeName:
        return ExchangeName.COINBASE

    @property
    def base_url(self) -> str:
        return "https://api.international.coinbase.com/api/"

    @property
    def exchange_info_url(self) -> str:
        return "v1/instruments"

    @property
    def exchange_symbol_field(self) -> str:
        return "symbol"

    def _get_instruments_info_from_exchange_info(self, exchange_info: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return exchange_info

    @property
    def unified_symbol_fields(self) -> tuple[str, ...]:
        return ("base_asset_name", "quote_asset_name")
