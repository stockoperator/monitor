from abc import ABC, abstractmethod
import asyncio
from logging import Logger
from aiohttp import ClientSession
from pathlib import Path
import fcntl
import os
import orjson
from typing import Any
import time

from connector.async_logger import null_logger
from connector.trading_types import Order, OrderSide, Position
from connector.events import Event, WebsocketConnectedEvent
from connector.websocket import WebsocketTransport
from connector.http_client import HttpResponse
from connector.rate_limiter import BaseRateLimiterHttpClient
from connector.utils import traceback_error_str


class BaseAccountService(ABC):
    def __init__(
        self,
        *,
        session: ClientSession,
        ws_url: str = "",
        logger: Logger = null_logger(),
        state_path: Path,
        http_client: BaseRateLimiterHttpClient,
        order_http_client: BaseRateLimiterHttpClient,
    ) -> None:
        self.logger = logger

        self._state_path = state_path
        self._state_tmp_path = state_path.with_suffix(state_path.suffix + ".tmp")
        self._state_lock_path = state_path.with_suffix(state_path.suffix + ".lock")
        self._state_lock_fd: int | None = None
        state_path.parent.mkdir(parents=True, exist_ok=True)
        self._save_lock: asyncio.Lock = asyncio.Lock()
        self._has_unsaved_changes: bool = False

        self.http_client = http_client
        self.order_http_client = order_http_client

        self.incoming_events: asyncio.Queue[Event] = asyncio.Queue()

        self.orders: dict[str, Order] = {}
        self.positions: dict[str, Position] = {}

        self.websocket_transport = WebsocketTransport(
            session=session,
            url=ws_url,
            logger=self.logger.getChild("ws"),
            on_message=self.handle_message,
            on_connected=lambda ws: self.incoming_events.put_nowait(WebsocketConnectedEvent(ws)),
        )

        self.wallet_balance: float = 0.0

    @abstractmethod
    async def run(self) -> None: ...

    @abstractmethod
    async def rest_place_order(self, order: Order) -> HttpResponse: ...

    @abstractmethod
    async def place_order(self, order: Order) -> None: ...

    @abstractmethod
    async def rest_cancel_order(self, symbol: str, client_order_id: str) -> HttpResponse: ...

    @abstractmethod
    async def rest_get_order(self, symbol: str, client_order_id: str) -> HttpResponse: ...

    @abstractmethod
    async def rest_get_balance(self) -> None: ...

    @abstractmethod
    def handle_message(self, message: str) -> None: ...

    @abstractmethod
    def _order_from_ws(self, data: dict[str, Any]) -> Order: ...

    @abstractmethod
    def _order_from_rest(self, data: dict[str, Any]) -> Order: ...

    async def _update_orders_from_rest(self) -> None:
        for order in list(self.orders.values()):
            if not order.is_live:
                continue
            try:
                response = await self.rest_get_order(symbol=order.symbol, client_order_id=order.client_order_id)
                if response.status != 200:
                    self.logger.error(f"{order.client_order_id}: status: {response.status}, data: {response.data!r}")
                    continue
                await self.update_order(self._order_from_rest(response.data))
            except asyncio.CancelledError:
                raise
            except Exception:
                self.logger.error(f"{order.client_order_id}: {traceback_error_str()}")

    async def update_order(self, info: Order) -> None:
        order = self.orders.get(info.client_order_id)
        if not order:
            return

        order.status = info.status

        if info.cum_exec_qty > order.cum_exec_qty:
            executed_qty = info.cum_exec_qty - order.cum_exec_qty
            quote = info.cum_quote - order.cum_quote
            if order.side == OrderSide.SELL:
                executed_qty *= -1

            order.cum_exec_qty = info.cum_exec_qty
            order.cum_quote = info.cum_quote

            self.update_position(symbol=order.symbol, executed_qty=executed_qty, quote=quote)

        if order.is_terminal:
            del self.orders[order.client_order_id]

        self._has_unsaved_changes = True

    def update_position(self, *, symbol: str, executed_qty: float, quote: float) -> None:
        if symbol in self.positions:
            position = self.positions[symbol]
            position.qty = round(position.qty + executed_qty, 10)
            if position.qty * executed_qty > 0:
                position.cum_entry_quote += quote
                position.entry_qty += abs(executed_qty)
            else:
                position.cum_exit_quote += quote
            if position.qty == 0.0:
                self.logger.info(
                    f"TRADE: symbol: {symbol}, entry_time: {position.entry_time}"
                    f", exit_time: {time.time_ns()/1_000_000}"
                    f", pnl: {int(position.cum_exit_quote-position.cum_entry_quote)}"
                )
                del self.positions[symbol]
        else:
            self.positions[symbol] = Position(
                symbol=symbol,
                qty=executed_qty,
                entry_qty=abs(executed_qty),
                cum_entry_quote=quote,
            )

    # --- persistence ------------------------------------------------------

    async def _load_from_disk(self) -> None:
        loaded = await asyncio.to_thread(self._load_state)
        if loaded is None:
            self.logger.info("no prior state; starting clean")
            return

        self.orders, self.positions = loaded
        self.logger.info(f"loaded state: {len(self.orders)} orders, {len(self.positions)} positions")

    async def _save(self) -> None:
        """Persist orders+positions. fsync runs in a worker thread so the event loop isn't blocked.

        The lock serializes concurrent writers — without it, two threads could clobber the same tmp file.
        """
        async with self._save_lock:
            orders_payload = {cid: order.to_dict() for cid, order in self.orders.items()}
            positions_payload = {sym: pos.to_dict() for sym, pos in self.positions.items()}
            await asyncio.to_thread(self._write_state, orders_payload, positions_payload)

    async def _save_loop(self, interval: float = 5.0) -> None:
        """Periodic flush for non-critical mutations. Clears the flag *before* the save so that
        any mutation arriving during the in-flight write re-flags and is picked up on the next tick.
        """
        while True:
            try:
                await asyncio.sleep(interval)
                if self._has_unsaved_changes:
                    self._has_unsaved_changes = False
                    await self._save()
            except asyncio.CancelledError:
                raise
            except Exception:
                self.logger.error(traceback_error_str())
                await asyncio.sleep(5)

    def _acquire_state_lock(self) -> None:
        """Take an exclusive flock on a sidecar file so a second process can't run on the same state.

        The lock is auto-released by the kernel on process death — no PID-file staleness on crash.
        Fails fast (RuntimeError) if another process already holds it; never blocks.
        """
        if self._state_lock_fd is not None:
            return
        fd = os.open(self._state_lock_path, os.O_RDWR | os.O_CREAT, 0o600)
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            os.close(fd)
            raise RuntimeError(f"state file already locked by another process: {self._state_lock_path}")
        self._state_lock_fd = fd

    def _release_state_lock(self) -> None:
        if self._state_lock_fd is None:
            return
        try:
            fcntl.flock(self._state_lock_fd, fcntl.LOCK_UN)
        finally:
            os.close(self._state_lock_fd)
            self._state_lock_fd = None

    def _load_state(self) -> tuple[dict[str, Order], dict[str, Position]] | None:
        if not self._state_path.exists():
            return None
        raw = self._state_path.read_bytes()
        if not raw:
            raise ValueError(f"state file is empty: {self._state_path}")
        data: dict[str, Any] = orjson.loads(raw)
        orders = {cid: Order.from_dict(o) for cid, o in data["orders"].items()}
        positions = {sym: Position.from_dict(p) for sym, p in data["positions"].items()}
        return orders, positions

    def _write_state(self, orders_payload: dict[str, dict[str, Any]], positions_payload: dict[str, dict[str, Any]]) -> None:
        """Atomic write: tmp file + fsync + rename + dir-fsync. Survives power loss."""
        payload = orjson.dumps(
            {"orders": orders_payload, "positions": positions_payload},
            option=orjson.OPT_INDENT_2,
        )
        fd = os.open(self._state_tmp_path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        try:
            os.write(fd, payload)
            os.fsync(fd)
        finally:
            os.close(fd)
        os.replace(self._state_tmp_path, self._state_path)
        dir_fd = os.open(self._state_path.parent, os.O_DIRECTORY)
        try:
            os.fsync(dir_fd)
        finally:
            os.close(dir_fd)
