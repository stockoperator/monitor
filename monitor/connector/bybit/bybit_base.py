from monitor.connector.connector_old import BaseConnector, ExchangeName
from typing import Any


class BybitBase(BaseConnector):
    @property
    def name(self) -> ExchangeName:
        return ExchangeName.BYBIT

    @property
    def base_url(self) -> str:
        return "https://api.bybit.com/v5/"

    @property
    def exchange_symbol_field(self) -> str:
        return "symbol"

    @property
    def unified_symbol_fields(self) -> tuple[str, ...]:
        return ("baseCoin", "quoteCoin")

    def _get_instruments_info_from_exchange_info(self, exchange_info: dict[str, Any]) -> list[dict[str, Any]]:
        return exchange_info["result"]["list"]
