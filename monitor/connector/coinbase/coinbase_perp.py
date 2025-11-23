from connector.connector import MarketType
from connector.coinbase.coinbase_base import CoinbaseBase
from typing import Any


class CoinbasePerp(CoinbaseBase):
    @property
    def market_type(self) -> MarketType:
        return MarketType.PERPETUAL

    def _is_instrument_info_valid(self, inst_info: dict[str, Any]) -> bool:
        return inst_info["type"] == "PERP" and inst_info["trading_state"] == "TRADING" and inst_info["quote_asset_name"] == "USDC"
