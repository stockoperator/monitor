from aiohttp import ClientSession
import asyncio
from logging import Logger
from typing import Any
import orjson
from pathlib import Path

from connector.utils import run_periodic, traceback_error_str
from connector.events import Event, OrderUpdateEvent, WebsocketConnectedEvent
from connector.async_logger import null_logger
from connector.rate_limiter import BaseRateLimiterHttpClient
from connector.http_client import HTTPMethod, HttpResponse
from connector.account_service import BaseAccountService
from connector.trading_types import Order, OrderType, OrderStatus, OrderSide, TimeInForce

from connector.binance.binance_base import BinanceApiError, raise_for_status
from connector.binance.constants import (
    base_perp_url,
    perp_listen_key_url,
    ws_perp_private_url,
    perp_position_mode,
    perp_order_url,
    perp_balance_url,
)


class BinancePerpAccountService(BaseAccountService):
    def __init__(
        self,
        *,
        session: ClientSession,
        logger: Logger = null_logger(),
        state_path: Path,
        http_client: BaseRateLimiterHttpClient,
        order_http_client: BaseRateLimiterHttpClient,
    ) -> None:
        super().__init__(
            session=session,
            logger=logger,
            state_path=state_path,
            http_client=http_client,
            order_http_client=order_http_client,
        )

        self.listen_key: str = ""

    # --- listen key functions --------------------------------------------

    async def get_listen_key(self, http_method: HTTPMethod) -> tuple[str, str]:
        response = await self.http_client.request(method=http_method, url=base_perp_url + perp_listen_key_url, is_auth_required=True)
        listenKey = response.data.get("listenKey", "")
        return listenKey, response.data

    async def check_listen_key(self) -> None:
        listen_key, _ = await self.get_listen_key(HTTPMethod.PUT)
        if not listen_key or self.listen_key != listen_key:
            listen_key, data = await self.get_listen_key(HTTPMethod.POST)
        if not listen_key:
            raise BinanceApiError(f"check_listen_key: empty listenKey from POST. Data: {data}")

        if listen_key != self.listen_key:
            self.websocket_transport.ws_url = f"{ws_perp_private_url}/{listen_key}"
            if self.listen_key:
                ws = self.websocket_transport.ws
                if ws and not ws.closed:
                    await ws.close()
            self.listen_key = listen_key

    # --- rest functions --------------------------------------------------

    async def rest_place_order(self, order: Order) -> HttpResponse:
        params: dict[str, Any] = {
            "symbol": order.symbol,
            "side": order.side.value,
            "type": order.type.value,
            "quantity": order.qty,
            "newClientOrderId": order.client_order_id,
        }
        if order.type is OrderType.LIMIT:
            if order.price is None:
                raise ValueError(f"LIMIT order without price: {order.client_order_id}")
            params["price"] = order.price
            params["timeInForce"] = order.time_in_force.value
        if order.reduce_only:
            params["reduceOnly"] = "true"

        return await self.order_http_client.request(
            method=HTTPMethod.POST,
            url=base_perp_url + perp_order_url,
            params=params,
            is_auth_required=True,
        )

    async def rest_cancel_order(self, symbol: str, client_order_id: str) -> HttpResponse:
        return await self.http_client.request(
            method=HTTPMethod.DELETE,
            url=base_perp_url + perp_order_url,
            params={"symbol": symbol, "origClientOrderId": client_order_id},
            is_auth_required=True,
        )

    async def rest_get_order(self, symbol: str, client_order_id: str) -> HttpResponse:
        return await self.http_client.request(
            method=HTTPMethod.GET,
            url=base_perp_url + perp_order_url,
            params={"symbol": symbol, "origClientOrderId": client_order_id},
            is_auth_required=True,
        )

    async def rest_verify_one_way_mode(self) -> None:
        response = await self.http_client.request(
            method=HTTPMethod.GET,
            url=base_perp_url + perp_position_mode,
            is_auth_required=True,
        )
        raise_for_status(response, "rest_verify_one_way_mode")
        if response.data.get("dualSidePosition"):
            raise RuntimeError("This service requires ONE-WAY mode. Switch in the Binance UI: Settings → Position Mode → One-Way.")

    async def rest_get_balance(self) -> None:
        response = await self.http_client.request(
            method=HTTPMethod.GET,
            url=base_perp_url + perp_balance_url,
            is_auth_required=True,
        )
        raise_for_status(response, "rest_get_balance")
        for asset_info in response.data:
            if asset_info["asset"] == "USDT":
                self.wallet_balance = asset_info["balance"]
                break

    # --- WS / REST data parsing -------------------------------------------

    def _order_from_ws(self, data: dict[str, Any]) -> Order:
        d: dict[str, Any] = data["o"]
        return Order(
            client_order_id=d["c"],
            symbol=d["s"],
            qty=0.0,
            side=OrderSide.BUY,
            type=OrderType.LIMIT,
            time_in_force=TimeInForce.GTX,
            reduce_only=True,
            status=OrderStatus(d["X"]),
            cum_exec_qty=float(d["z"]),
            cum_quote=float(d["ap"]) * float(d["z"]),
        )

    def _order_from_rest(self, data: dict[str, Any]) -> Order:
        if "code" in data:
            raise BinanceApiError(f"_order_from_rest error payload: code: {data['code']}, msg: {data.get('msg')!r}")
        return Order(
            client_order_id=data["clientOrderId"],
            symbol=data["symbol"],
            qty=0.0,
            side=OrderSide.BUY,
            type=OrderType.LIMIT,
            time_in_force=TimeInForce.GTX,
            reduce_only=True,
            status=OrderStatus(data["status"]),
            cum_exec_qty=float(data["executedQty"]),
            cum_quote=float(data["cumQuote"]),
        )

    # --- common functions ------------------------------------------------

    async def imcoming_event_loop(self) -> None:
        while True:
            event = await self.incoming_events.get()
            try:
                await self.handle_event(event)
            except asyncio.CancelledError:
                raise
            except Exception:
                self.logger.error(traceback_error_str())
                await asyncio.sleep(5)

    async def check_listen_key_loop(self) -> None:
        await run_periodic("listen-key", 25, self.check_listen_key, self.logger)

    async def update_orders_loop(self) -> None:
        await run_periodic("update-orders", 25, self._update_orders_from_rest, self.logger)

    async def update_balance_loop(self) -> None:
        await run_periodic("update-balance", 61, self.rest_get_balance, self.logger)

    async def place_order(self, order: Order) -> None:
        """Place an order. Trust-but-verify: any failure after POST is sent triggers a GET /order
        lookup, because the request may have landed on the exchange even if our response was lost
        (network blip, HTTP 5xx, Binance code -1007 "execution status unknown").
        """
        try:
            response = await self.rest_place_order(order)
            raise_for_status(response, "place_order")
            data: dict[str, Any] = response.data
            if "code" in data:
                # Binance can return 200 with `{"code": -1007, "msg": "execution status unknown"}`
                # on a state-changing call — the order may or may not have landed.
                raise BinanceApiError(f"place_order 200 with code: {data['code']}, msg: {data.get('msg')!r}")
            if data.get("clientOrderId") != order.client_order_id:
                raise BinanceApiError(f"place_order ack COID mismatch: expected: {order.client_order_id!r}, got: {data!r}")
            order.status = OrderStatus(data["status"])
        except asyncio.CancelledError:
            raise
        except Exception:
            self.logger.error(f"POST outcome unknown: {traceback_error_str()}; verifying via GET")
            await self._confirm_via_get(order)
            return

        self.orders[order.client_order_id] = order
        await self._save()
        self.logger.info(f"ok: {data}")

    async def _confirm_via_get(self, order: Order) -> None:
        """Ask the exchange whether our POST actually landed and record accordingly.

        Outcomes:
          - 200: order is on the exchange; record it and apply any fills that already happened.
          - -2013: order never reached the matching engine; nothing to do.
          - anything else: state is still unknown — bubble up so the caller (strategy) sees it.
        """
        response = await self.rest_get_order(order.symbol, order.client_order_id)
        data: dict[str, Any] = response.data

        if data.get("code") == -2013:
            self.logger.info(f"{order.client_order_id} did not reach exchange")
            return

        if response.status != 200:
            raise BinanceApiError(f"inconclusive: status: {response.status}, data: {data!r}")

        self.orders[order.client_order_id] = order
        await self.update_order(self._order_from_rest(data))
        await self._save()
        self.logger.error(f"recovered: {data}")

    async def handle_event(self, event: Event) -> None:
        if isinstance(event, WebsocketConnectedEvent):
            await self.check_listen_key()
            await self._update_orders_from_rest()
        elif isinstance(event, OrderUpdateEvent):
            await self.update_order(event.order)

    def _update_balance_from_ws(self, data: dict[str, Any]) -> None:
        a: dict[str, Any] = data["a"]
        for b in a.get("B", []):
            if b["a"] == "USDT":
                self.wallet_balance = float(b["wb"])

    def handle_message(self, message: str) -> None:
        self.logger.info(f"message: {message}")

        data: dict[str, Any] = orjson.loads(message)
        event_type = data.get("e")

        if event_type == "ORDER_TRADE_UPDATE":
            order = self._order_from_ws(data)
            self.incoming_events.put_nowait(OrderUpdateEvent(order))
        elif event_type == "ACCOUNT_UPDATE":
            self._update_balance_from_ws(data)

    async def run(self) -> None:
        await self.rest_verify_one_way_mode()
        await self.check_listen_key()
        await self.rest_get_balance()

        self._acquire_state_lock()
        try:
            await self._load_from_disk()
            async with asyncio.TaskGroup() as tg:
                tg.create_task(self.websocket_transport.loop())
                tg.create_task(self.imcoming_event_loop())
                tg.create_task(self._save_loop())
                tg.create_task(self.check_listen_key_loop())
                tg.create_task(self.update_orders_loop())
                tg.create_task(self.update_balance_loop())
        finally:
            self._release_state_lock()
