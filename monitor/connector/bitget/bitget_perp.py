from connector.connector import MarketType
from connector.bitget.bitget_base import BitgetBase
from typing import Any


class BitgetPerp(BitgetBase):
    @property
    def market_type(self) -> MarketType:
        return MarketType.PERPETUAL

    @property
    def exchange_info_url(self) -> str:
        return "mix/market/contracts?productType=USDT-FUTURES"

    @property
    def instrument_validation_dict(self) -> dict[str, Any]:
        return {
            "symbolType": "perpetual",
            "symbolStatus": "normal",
        }
