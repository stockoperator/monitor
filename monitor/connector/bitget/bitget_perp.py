from connector.connector import MarketType, HTTPMethod, Instrument
from connector.bitget.bitget_base import BitgetBase
from typing import Any

BASE_URL = "https://api.bitget.com/api/v2/"
EXCHANGE_INFO_URL = "mix/market/contracts"


class BitgetPerp(BitgetBase):
    @property
    def market_type(self) -> MarketType:
        return MarketType.PERPETUAL

    async def _request_exchange_info(self) -> dict[str, Any]:
        params = {"productType": "USDT-FUTURES"}
        return await self._request(HTTPMethod.GET, url=BASE_URL + EXCHANGE_INFO_URL, params=params)

    def _is_instrument_info_valid(self, inst_info: dict[str, Any]) -> bool:
        return inst_info["symbolType"] == "perpetual" and inst_info["symbolStatus"] == "normal"

    def _make_instrument_from_instrument_info(self, instrument_info: dict[str, Any]) -> Instrument:
        instrument = Instrument(
            exchange=self.name,
            market_type=self.market_type,
            exchange_symbol=instrument_info["symbol"],
            unified_symbol=self._unify_symbol(instrument_info),
        )
        return instrument
