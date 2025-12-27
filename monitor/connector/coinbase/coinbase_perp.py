from connector.connector import MarketType
from connector.coinbase.coinbase_base import CoinbaseBase
from typing import Any


class CoinbasePerp(CoinbaseBase):
    @property
    def market_type(self) -> MarketType:
        return MarketType.PERPETUAL

    @property
    def instrument_validation_dict(self) -> dict[str, Any]:
        return {
            "type": "PERP",
            "trading_state": "TRADING",
            "quote_asset_name": "USDC",
        }
