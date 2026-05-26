from typing import Any, Type
from logging import Logger

from connector.account_service import BaseAccountService
from connector.async_logger import null_logger
from connector.base_classes import MarketType
from connector.http_client import BaseHttpClient
from connector.rate_limiter import LimitWindow, BaseRateLimiterHttpClient
from connector.instrument import BaseInstrumentManager, Instrument
from connector.kline_service import BaseKlineService

from connector.binance.constants import SPOT_IP_WEIGHT_BUDGET, IP_WEIGHT_HEADER
from connector.binance.binance_base import (
    BinanceBase,
    BinanceHttpClientBase,
    BinanceBaseInstrumentManager,
    BinanceBaseKlineService,
    BinanceBasePublicRateLimiter,
)
from connector.binance.constants import (
    IP_WEIGHT_HEADER,
    SPOT_IP_WEIGHT_BUDGET,
    ORDER_10S_HEADER,
    SPOT_ORDER_10S_BUDGET,
    SPOT_ORDER_1D_HEADER,
    SPOT_ORDER_1D_BUDGET,
)
from connector.binance.constants import base_spot_url, spot_exchange_info_url, ws_spot_url, spot_klines_url


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

    def make_instrument_from_instrument_info(self, instrument_info: dict[str, Any]) -> Instrument:
        unify_symbol = instrument_info["baseAsset"] + instrument_info["quoteAsset"]

        return Instrument(exchange_symbol=instrument_info["symbol"], unified_symbol=unify_symbol)

    async def update_leverage_brackets(self) -> None: ...


class BinanceSpotKlineService(BinanceBaseKlineService):
    @property
    def ws_url(self) -> str:
        return ws_spot_url

    @property
    def klines_url(self) -> str:
        return base_spot_url + spot_klines_url

    @property
    def rest_limit(self) -> int:
        return 1000


class BinanceSpotPublicRateLimiter(BinanceBasePublicRateLimiter):
    def __init__(
        self,
        *,
        http_client: BaseHttpClient,
        logger: Logger = null_logger(),
    ) -> None:
        limit_windows = [
            LimitWindow(
                weight_limit=SPOT_IP_WEIGHT_BUDGET,
                window_seconds=60,
                response_header=IP_WEIGHT_HEADER,
            )
        ]

        super().__init__(
            http_client=http_client,
            limit_windows=limit_windows,
            logger=logger,
        )


class BinanceSpotOrderRateLimiter(BinanceBasePublicRateLimiter):
    def __init__(
        self,
        *,
        http_client: BaseHttpClient,
        logger: Logger = null_logger(),
    ) -> None:
        limit_windows = [
            LimitWindow(
                weight_limit=SPOT_ORDER_10S_BUDGET,
                window_seconds=10,
                response_header=ORDER_10S_HEADER,
            ),
            LimitWindow(
                weight_limit=SPOT_ORDER_1D_BUDGET,
                window_seconds=60 * 60 * 24,
                response_header=SPOT_ORDER_1D_HEADER,
            ),
        ]

        super().__init__(
            http_client=http_client,
            limit_windows=limit_windows,
            logger=logger,
        )


class BinanceSpot(BinanceBase):
    @property
    def market_type(self) -> MarketType:
        return MarketType.SPOT

    @property
    def http_client_type(self) -> Type[BaseHttpClient]:
        return BinanceHttpClientBase

    @property
    def public_http_client_type(self) -> Type[BaseRateLimiterHttpClient]:
        return BinanceSpotPublicRateLimiter

    @property
    def order_http_client_type(self) -> Type[BaseRateLimiterHttpClient]:
        return BinanceSpotOrderRateLimiter

    @property
    def instrument_manager_type(self) -> Type[BaseInstrumentManager]:
        return BinanceSpotInstrumentManager

    @property
    def kline_service_type(self) -> Type[BaseKlineService]:
        return BinanceSpotKlineService

    @property
    def account_service_type(self) -> Type[BaseAccountService] | None:
        return None
