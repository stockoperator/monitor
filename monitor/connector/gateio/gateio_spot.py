from connector.connector import MarketType, HTTPMethod, Instrument
from connector.gateio.gateio_base import GateioBase
from typing import Any

BASE_URL = "https://api.gateio.ws/api/v4/"
EXCHANGE_INFO_URL = "spot/currency_pairs"


class GateioSpot(GateioBase):
    @property
    def market_type(self) -> MarketType:
        return MarketType.SPOT

    async def _request_exchange_info(self) -> dict[str, Any]:
        """
        Docs: https://www.gate.com/docs/developers/apiv4/en/#query-all-supported-currency-pairs
        """
        exchange_info = await self._request(HTTPMethod.GET, url=BASE_URL + EXCHANGE_INFO_URL)
        return {"data": exchange_info}

    def _get_instruments_info_from_exchange_info(self, exchange_info: dict[str, Any]) -> list[dict[str, Any]]:
        return exchange_info["data"]

    def _unify_symbol(self, instrument_info: dict[str, Any]) -> str:
        return f'{instrument_info["base"]}{instrument_info["quote"]}'.upper()

    def _is_instrument_info_valid(self, inst_info: dict[str, Any]) -> bool:
        return inst_info["quote"] == "USDT" and inst_info["trade_status"] == "tradable" and inst_info["type"] == "normal"

    def _make_instrument_from_instrument_info(self, instrument_info: dict[str, Any]) -> Instrument:
        instrument = Instrument(
            exchange=self.name,
            market_type=self.market_type,
            exchange_symbol=instrument_info["id"],
            unified_symbol=self._unify_symbol(instrument_info),
        )
        return instrument
