from connector.connector import MarketType
from connector.coinbase.coinbase_base import CoinbaseBase
from typing import Any


class CoinbaseSpot(CoinbaseBase):
    @property
    def market_type(self) -> MarketType:
        return MarketType.SPOT

    def _is_instrument_info_valid(self, inst_info: dict[str, Any]) -> bool:
        return inst_info["type"] == "SPOT" and inst_info["trading_state"] == "TRADING" and inst_info["quote_asset_name"] == "USDC"
