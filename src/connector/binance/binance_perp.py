from typing import Any, Type, cast
from logging import Logger
import orjson

from connector.account_service import BaseAccountService
from connector.async_logger import null_logger
from connector.base_classes import MarketType
from connector.http_client import BaseHttpClient
from connector.rate_limiter import BaseRateLimiterHttpClient, LimitWindow
from connector.instrument import BaseInstrumentManager, Instrument, LeverageBracket
from connector.kline_service import BaseKlineService
from connector.funding_service import BaseFundingService
from connector.http_client import HTTPMethod
from connector.trading_types import FundingRate
from connector.utils import float_or_none

from connector.binance.binance_account import BinancePerpAccountService
from connector.binance.constants import (
    PERP_IP_WEIGHT_BUDGET,
    IP_WEIGHT_HEADER,
    ORDER_10S_HEADER,
    PERP_ORDER_1M_HEADER,
    PERP_ORDER_10S_BUDGET,
    PERP_ORDER_1M_BUDGET,
)

from connector.binance.binance_base import (
    BinanceBase,
    BinanceBaseInstrumentManager,
    BinanceHttpClientBase,
    BinanceBaseKlineService,
    BinanceBasePublicRateLimiter,
)
from connector.binance.constants import (
    base_perp_url,
    perp_exchange_info_url,
    perp_klines_url,
    ws_perp_market_url,
    perp_leverage_brackets_url,
    perp_mark_price_all_channel,
)


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
        filters = {f["filterType"]: f for f in instrument_info["filters"]}
        price_f: dict[str, Any] = filters.get("PRICE_FILTER", {})
        lot_f: dict[str, Any] = filters.get("MARKET_LOT_SIZE", {})
        notional_f: dict[str, Any] = filters.get("MIN_NOTIONAL", {})

        return Instrument(
            exchange_symbol=instrument_info["symbol"],
            unified_symbol=instrument_info["baseAsset"] + instrument_info["quoteAsset"],
            price_step=float_or_none(price_f.get("tickSize")),
            min_price=float_or_none(price_f.get("minPrice")),
            max_price=float_or_none(price_f.get("maxPrice")),
            qty_step=float_or_none(lot_f.get("stepSize")),
            min_qty=float_or_none(lot_f.get("minQty")),
            max_qty=float_or_none(lot_f.get("maxQty")),
            min_notional=float_or_none(notional_f.get("notional")),
            liquidation_fee=float(instrument_info["liquidationFee"]),
        )

    async def update_leverage_brackets(self) -> None:
        def bracket_from_dict(data: dict[str, Any]) -> LeverageBracket:
            initial_leverage = float(data["initialLeverage"])
            maint_margin_ratio = float(data["maintMarginRatio"])
            notional_floor = int(data["notionalFloor"])
            notional_cap = int(data["notionalCap"])
            cumulative_amount = int(data["cum"])
            return LeverageBracket(
                initial_leverage=initial_leverage,
                maint_margin_ratio=maint_margin_ratio,
                notional_floor=notional_floor,
                notional_cap=notional_cap,
                cumulative_amount=cumulative_amount,
            )

        response = await self.http_client.request(
            method=HTTPMethod.GET,
            url=base_perp_url + perp_leverage_brackets_url,
            is_auth_required=True,
        )
        data: list[dict[str, Any]] = response.data

        for symbol_data in data:
            symbol: str = symbol_data["symbol"]
            instrument = self.get(symbol)
            if instrument:
                instrument.leverage_brackets = tuple(bracket_from_dict(data) for data in symbol_data["brackets"])


class BinancePerpKlineService(BinanceBaseKlineService):
    @property
    def ws_url(self) -> str:
        return ws_perp_market_url

    @property
    def klines_url(self) -> str:
        return base_perp_url + perp_klines_url

    @property
    def rest_limit(self) -> int:
        return 499


class BinancePerpFundingService(BaseFundingService):
    @property
    def ws_url(self) -> str:
        return ws_perp_market_url

    def get_channel(self, symbol: str) -> str:
        # required by BaseDataService for per-symbol fan-out, but unused here: this service
        # subscribes to ONE all-market stream (see subscribe_all), never per-symbol channels
        raise NotImplementedError("funding uses the all-market stream, not per-symbol channels")

    def make_subscribe_message(self, channel_batch: list[str]) -> bytes:
        return orjson.dumps({"method": "SUBSCRIBE", "params": channel_batch})

    async def subscribe_all(self) -> None:
        # the all-market stream already carries every instrument — one subscription, no per-symbol fan-out
        await self.subscribe_channels([perp_mark_price_all_channel])

    async def subscribe(self, instruments: set[str]) -> None:
        # newly listed instruments show up in the all-market stream automatically; nothing to do
        return

    def handle_message(self, message: str) -> None:
        data: Any = orjson.loads(message)
        if not isinstance(data, list):
            return  # subscribe ack / control frame

        for item in cast(list[dict[str, Any]], data):
            rate = item.get("r")
            symbol = item["s"]
            if not rate:
                continue
            self.funding[symbol] = FundingRate(
                symbol=item["s"],
                rate=float(rate),
                next_time=int(item["T"]),
            )


class BinancePerpPublicRateLimiter(BinanceBasePublicRateLimiter):
    def __init__(
        self,
        *,
        http_client: BaseHttpClient,
        logger: Logger = null_logger(),
    ) -> None:
        limit_windows = [
            LimitWindow(
                weight_limit=PERP_IP_WEIGHT_BUDGET,
                window_seconds=60,
                response_header=IP_WEIGHT_HEADER,
            )
        ]

        super().__init__(
            http_client=http_client,
            limit_windows=limit_windows,
            logger=logger,
        )


class BinancePerpOrderRateLimiter(BinanceBasePublicRateLimiter):
    def __init__(
        self,
        *,
        http_client: BaseHttpClient,
        logger: Logger = null_logger(),
    ) -> None:
        limit_windows = [
            LimitWindow(
                weight_limit=PERP_ORDER_10S_BUDGET,
                window_seconds=10,
                response_header=ORDER_10S_HEADER,
            ),
            LimitWindow(
                weight_limit=PERP_ORDER_1M_BUDGET,
                window_seconds=60,
                response_header=PERP_ORDER_1M_HEADER,
            ),
        ]

        super().__init__(
            http_client=http_client,
            limit_windows=limit_windows,
            logger=logger,
        )


class BinancePerp(BinanceBase):
    @property
    def market_type(self) -> MarketType:
        return MarketType.PERP

    @property
    def http_client_type(self) -> Type[BaseHttpClient]:
        return BinanceHttpClientBase

    @property
    def public_http_client_type(self) -> Type[BaseRateLimiterHttpClient]:
        return BinancePerpPublicRateLimiter

    @property
    def order_http_client_type(self) -> Type[BaseRateLimiterHttpClient]:
        return BinancePerpOrderRateLimiter

    @property
    def instrument_manager_type(self) -> Type[BaseInstrumentManager]:
        return BinancePerpInstrumentManager

    @property
    def kline_service_type(self) -> Type[BaseKlineService]:
        return BinancePerpKlineService

    @property
    def funding_service_type(self) -> Type[BaseFundingService] | None:
        return BinancePerpFundingService

    @property
    def account_service_type(self) -> Type[BaseAccountService] | None:
        return BinancePerpAccountService
