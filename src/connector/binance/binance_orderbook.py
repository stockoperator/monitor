from connector.base_classes import BaseOrderbook, PartialOrderbook
from connector.binance.binance_base import BinanceBaseOrderbookService


class BinancePartialOrderbookService(BinanceBaseOrderbookService):
    @property
    def orderbook_type(self) -> type[BaseOrderbook]:
        return PartialOrderbook
