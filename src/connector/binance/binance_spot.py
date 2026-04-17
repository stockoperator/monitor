from typing import Any, Type

from connector.base_classes import MarketType
from connector.http_client import BaseHttpClient
from connector.instrument import BaseInstrumentManager
from connector.orderbook_service import BaseOrderbookService
from connector.public_trade_service import BasePublicTradeService

from connector.binance.binance_base import BinanceBase, BinanceHttpClientBase, BinanceBaseInstrumentManager
from connector.binance.binance_orderbook import BinancePartialOrderbookService
from connector.binance.binance_public_trade import BinancePublicTradeService
from connector.binance.constants import base_spot_url, spot_exchange_info_url, ws_spot_url


class BinanceSpotInstrumentManager(BinanceBaseInstrumentManager):
    @property
    def exchange_info_url(self) -> str:
        return base_spot_url + spot_exchange_info_url + "?symbolStatus=TRADING&showPermissionSets=false&permissions=SPOT"
        # return base_spot_url + spot_exchange_info_url + "?symbol=BTCUSDT"

    @property
    def instrument_validation_dict(self) -> dict[str, Any]:
        return {
            "status": "TRADING",
            "quoteAsset": "USDT",
        }

    async def update_leverage_brackets(self) -> None: ...


class BinanceSpotPartialOrderbookService(BinancePartialOrderbookService):
    @property
    def ws_url(self) -> str:
        return ws_spot_url

    def get_channel(self, symbol: str) -> str:
        return f"{symbol.lower()}@bookTicker"  # @depth<levels> OR @depth<levels>@500ms OR @depth<levels>@100ms

    def handle_message(self, message: str) -> None:
        # Fast path: full JSON parsing is too slow, parse only 'u' and 's' manually
        pos = message.find('"u":')
        if pos == -1:
            return

        pos = message.find('"s":')
        if pos == -1:
            return

        s_start = message.find('"', pos + 4) + 1
        s_end = message.find('"', s_start)
        symbol = message[s_start:s_end]

        orderbook = self[symbol]
        orderbook.message = message


class BinanceSpotPublicTradeService(BinancePublicTradeService):
    @property
    def ws_url(self) -> str:
        return ws_spot_url


class BinanceSpot(BinanceBase):
    @property
    def market_type(self) -> MarketType:
        return MarketType.SPOT

    @property
    def http_client_type(self) -> Type[BaseHttpClient]:
        return BinanceHttpClientBase

    @property
    def instrument_manager_type(self) -> Type[BaseInstrumentManager]:
        return BinanceSpotInstrumentManager

    @property
    def orderbook_service_type(self) -> Type[BaseOrderbookService]:
        return BinanceSpotPartialOrderbookService

    @property
    def public_trade_service_type(self) -> Type[BasePublicTradeService]:
        return BinanceSpotPublicTradeService
