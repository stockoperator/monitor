from connector.connector import AbstractConnector, ExchangeName
from typing import Any


class OkxBase(AbstractConnector):
    """
    Docs: https://www.okx.com/docs-v5/en
    Docs: https://www.okx.com/docs-v5/en/#public-data-rest-api-get-instruments
    """

    @property
    def name(self) -> ExchangeName:
        return ExchangeName.OKX

    @property
    def base_url(self) -> str:
        return "https://www.okx.com/api/v5/"

    @property
    def exchange_symbol_field(self) -> str:
        return "instId"

    def _get_instruments_info_from_exchange_info(self, exchange_info: dict[str, Any]) -> list[dict[str, Any]]:
        return exchange_info["data"]
