from logging import Logger
from aiohttp import ClientSession

from connector.async_logger import null_logger
from connector.rate_limiter import BaseRateLimiterHttpClient
from connector.instrument import BaseInstrumentManager
from connector.data_service import BaseDataService
from connector.trading_types import FundingRate


class BaseFundingService(BaseDataService):
    """Tracks upcoming funding (rate + next settlement time) per instrument from a market WS stream.

    Funding is public market data, so this rides the public market socket alongside the kline service —
    not the private account stream. Holds the latest snapshot per symbol; nothing is persisted.
    """

    def __init__(
        self,
        *,
        session: ClientSession,
        http_client: BaseRateLimiterHttpClient,
        instrument_manager: BaseInstrumentManager,
        logger: Logger = null_logger(),
    ) -> None:
        super().__init__(
            session=session,
            http_client=http_client,
            instrument_manager=instrument_manager,
            logger=logger,
        )
        self.funding: dict[str, FundingRate] = {}

    def __getitem__(self, symbol: str) -> FundingRate | None:
        return self.funding.get(symbol)
