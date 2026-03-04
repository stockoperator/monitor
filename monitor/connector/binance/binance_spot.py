from typing import Any, Type

from connector.base_classes import MarketType, OrderbookDelta
from connector.http_client import BaseHttpClient
from connector.instrument import BaseInstrumentManager, Instrument
from connector.orderbook_service import BaseOrderbookService
from connector.public_trade_service import BasePublicTradeService
from connector.data_parser import BaseDataParser
from connector.events import OrderbookDeltaEvent

from connector.binance.binance_base import BinanceBase, BinanceHttpClientBase, BinanceBaseInstrumentManager
from connector.binance.binance_orderbook import BinanceOrderbookService, BinanceOrderbookDataParser
from connector.binance.binance_public_trade import BinancePublicTradeService
from connector.binance.constants import base_spot_url, spot_exchange_info_url, ws_spot_url


class BinanceSpotInstrumentManager(BinanceBaseInstrumentManager):
    @property
    def exchange_info_url(self) -> str:
        return base_spot_url + spot_exchange_info_url

    @property
    def instrument_validation_dict(self) -> dict[str, Any]:
        return {
            "status": "TRADING",
            "quoteAsset": "USDT",
        }

    def make_instrument_from_instrument_info(self, instrument_info: dict[str, Any]) -> Instrument:
        unify_symbol = instrument_info["baseAsset"] + instrument_info["quoteAsset"]

        return Instrument(
            exchange=self.name,
            market_type=self.market_type,
            exchange_symbol=instrument_info["symbol"],
            unified_symbol=unify_symbol,
        )


class BinanceSpotOrderbookDataParser(BinanceOrderbookDataParser):
    def _parse_orderbook_delta(self, data: dict[str, Any]) -> OrderbookDelta:
        return OrderbookDelta(
            symbol=str(data["s"]),
            exchange_ts_ms=int(data["E"]),
            transaction_ts_ms=int(data["E"]),
            first_id=int(data["U"]),
            last_id=int(data["u"]),
            prev_last_id=-1,  # 0 нельзя тк. на него логика зашита
            bids=self._parse_price_levels(data.get("b", [])),
            asks=self._parse_price_levels(data.get("a", [])),
        )

    async def route_message(self, data: dict[str, Any]) -> None:
        event_type = data.get("e", "")

        if event_type == "depthUpdate":
            orderbook_delta = self._parse_orderbook_delta(data)
            self.on_event(OrderbookDeltaEvent(orderbook_delta))


class BinanceSpotOrderbookService(BinanceOrderbookService):
    @property
    def ws_url(self) -> str:
        return ws_spot_url

    @property
    def data_parser_type(self) -> Type[BaseDataParser]:
        return BinanceSpotOrderbookDataParser

    def is_gap(self, delta: OrderbookDelta) -> bool:
        orderbook = self._items[delta.symbol]
        result = orderbook.last_id + 1 != delta.first_id and orderbook.last_id != 0
        if result:
            self.logger.info(f"Gap detected. last_id={orderbook.last_id}, prev_last_id={delta.first_id-1}")
        return result


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
        return BinanceSpotOrderbookService

    @property
    def public_trade_service_type(self) -> Type[BasePublicTradeService]:
        return BinanceSpotPublicTradeService
