from connector.connector import MarketType, HTTPMethod, Instrument
from connector.binance.binance_base import BinanceBase
from typing import Any

BASE_URL = "https://api.binance.com/api/"
EXCHANGE_INFO_URL = "v3/exchangeInfo"


class BinanceSpot(BinanceBase):
    @property
    def market_type(self) -> MarketType:
        return MarketType.SPOT

    async def _request_exchange_info(self) -> dict[str, Any]:
        return await self._request(HTTPMethod.GET, url=BASE_URL + EXCHANGE_INFO_URL)

    def _is_instrument_info_valid(self, inst_info: dict[str, Any]) -> bool:
        return inst_info["status"] == "TRADING" and inst_info["quoteAsset"] == "USDT"

    def _make_instrument_from_instrument_info(self, instrument_info: dict[str, Any]) -> Instrument:
        instrument = Instrument(
            exchange=self.name,
            market_type=self.market_type,
            exchange_symbol=instrument_info["symbol"],
            unified_symbol=self._unify_symbol(instrument_info),
        )
        return instrument
