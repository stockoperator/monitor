from connector.connector import MarketType, HTTPMethod, Instrument
from connector.mexc.mexc_base import MexcBase
from typing import Any

BASE_URL = "https://contract.mexc.com/api/"
EXCHANGE_INFO_URL = "v1/contract/detail"


class MexcPerp(MexcBase):
    @property
    def market_type(self) -> MarketType:
        return MarketType.PERPETUAL

    async def _request_exchange_info(self) -> dict[str, Any]:
        """
        Docs: https://www.mexc.com/api-docs/futures/market-endpoints#get-contract-info
        """
        return await self._request(HTTPMethod.GET, url=BASE_URL + EXCHANGE_INFO_URL)

    def _get_instruments_info_from_exchange_info(self, exchange_info: dict[str, Any]) -> list[dict[str, Any]]:
        return exchange_info["data"]

    def _unify_symbol(self, instrument_info: dict[str, Any]) -> str:
        return f'{instrument_info["baseCoin"]}{instrument_info["quoteCoin"]}'.upper()

    def _is_instrument_info_valid(self, inst_info: dict[str, Any]) -> bool:
        return (
            inst_info["state"] == 0 and inst_info["futureType"] == 1 and inst_info["quoteCoin"] == "USDT"
        )  # inst_info["apiAllowed"] все выключены для api торговли

    def _make_instrument_from_instrument_info(self, instrument_info: dict[str, Any]) -> Instrument:
        instrument = Instrument(
            exchange=self.name,
            market_type=self.market_type,
            exchange_symbol=instrument_info["symbol"],
            unified_symbol=self._unify_symbol(instrument_info),
        )
        return instrument
