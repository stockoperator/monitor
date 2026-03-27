from typing import Any, Type

from connector.base_classes import MarketType
from connector.http_client import BaseHttpClient
from connector.instrument import BaseInstrumentManager, Instrument
from connector.public_trade_service import BasePublicTradeService
from connector.orderbook_service import BaseOrderbookService

from connector.binance.binance_orderbook import BinancePartialOrderbookService
from connector.binance.binance_public_trade import BinancePublicTradeService
from connector.binance.binance_base import BinanceBase, BinanceBaseInstrumentManager, BinanceHttpClientBase
from connector.binance.constants import base_perp_url, perp_exchange_info_url, ws_perp_url


class BinancePerpInstrumentManager(BinanceBaseInstrumentManager):
    @property
    def exchange_info_url(self) -> str:
        return base_perp_url + perp_exchange_info_url

    @property
    def instrument_validation_dict(self) -> dict[str, Any]:
        return {
            "status": "TRADING",
            "contractType": "PERPETUAL",
            "quoteAsset": "USDT",
        }

    def make_instrument_from_instrument_info(self, instrument_info: dict[str, Any]) -> Instrument:
        unify_symbol = instrument_info["baseAsset"] + instrument_info["quoteAsset"]

        return Instrument(
            exchange_symbol=instrument_info["symbol"],
            unified_symbol=unify_symbol,
        )


class BinancePerpPartialOrderbookService(BinancePartialOrderbookService):
    @property
    def ws_url(self) -> str:
        return ws_perp_url

    def get_channel(self, symbol: str) -> str:
        return f"{symbol.lower()}@depth20"  # @depth<levels> OR @depth<levels>@500ms OR @depth<levels>@100ms

    def handle_message(self, message: str) -> None:
        pos = message.find('"e":')
        if pos == -1:
            return
        e_start = message.find('"', pos + 4) + 1
        e_end = message.find('"', e_start)
        event_type = message[e_start:e_end]

        if event_type != "depthUpdate":
            return

        pos = message.find('"s":')
        if pos == -1:
            return

        s_start = message.find('"', pos + 4) + 1
        s_end = message.find('"', s_start)
        symbol = message[s_start:s_end]

        orderbook = self[symbol]
        orderbook.message = message


class BinancePerpPublicTradeService(BinancePublicTradeService):
    @property
    def ws_url(self) -> str:
        return ws_perp_url


class BinancePerp(BinanceBase):
    @property
    def market_type(self) -> MarketType:
        return MarketType.PERPETUAL

    @property
    def http_client_type(self) -> Type[BaseHttpClient]:
        return BinanceHttpClientBase

    @property
    def instrument_manager_type(self) -> Type[BaseInstrumentManager]:
        return BinancePerpInstrumentManager

    @property
    def orderbook_service_type(self) -> Type[BaseOrderbookService]:
        return BinancePerpPartialOrderbookService

    @property
    def public_trade_service_type(self) -> Type[BasePublicTradeService]:
        return BinancePerpPublicTradeService
