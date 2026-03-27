from logging import Logger
from aiohttp import ClientSession
from abc import abstractmethod

from connector.async_logger import null_logger
from connector.instrument import BaseInstrumentManager
from connector.data_service import BaseDataService
from connector.base_classes import BaseOrderbook


class BaseOrderbookService(BaseDataService):
    def __init__(
        self,
        *,
        session: ClientSession,
        instruments: BaseInstrumentManager,
        logger: Logger = null_logger(),
    ) -> None:
        super().__init__(
            session=session,
            instruments=instruments,
            logger=logger,
        )
        self._items: dict[str, BaseOrderbook] = {}

    @property
    @abstractmethod
    def orderbook_type(self) -> type[BaseOrderbook]: ...

    def __getitem__(self, symbol: str) -> BaseOrderbook:
        if symbol not in self._items:
            self._items[symbol] = self.orderbook_type()
        return self._items[symbol]
