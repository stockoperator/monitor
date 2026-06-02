from dataclasses import dataclass, field
from enum import Enum
from typing import Any
import time


class OrderSide(Enum):
    BUY = "BUY"
    SELL = "SELL"


class OrderType(Enum):
    LIMIT = "LIMIT"
    MARKET = "MARKET"


class TimeInForce(Enum):
    GTC = "GTC"
    IOC = "IOC"
    FOK = "FOK"
    GTX = "GTX"  # post-only (Binance perp)


class OrderStatus(Enum):
    NEW = "NEW"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    FILLED = "FILLED"
    CANCELED = "CANCELED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"


_TERMINAL_STATUSES = frozenset({OrderStatus.FILLED, OrderStatus.CANCELED, OrderStatus.REJECTED, OrderStatus.EXPIRED})
_LIVE_STATUSES = frozenset({OrderStatus.NEW, OrderStatus.PARTIALLY_FILLED})


class PositionSide(Enum):
    """One-way mode: only BOTH is used. Hedge mode uses LONG / SHORT (not supported here)."""

    BOTH = "BOTH"
    LONG = "LONG"
    SHORT = "SHORT"


@dataclass(kw_only=True, slots=True)
class Order:
    client_order_id: str = field(default_factory=lambda: str(time.time_ns()))
    symbol: str  # unified
    price: float | None = None
    qty: float
    side: OrderSide
    type: OrderType
    time_in_force: TimeInForce
    reduce_only: bool = False
    status: OrderStatus
    cum_exec_qty: float = 0.0
    cum_quote: float = 0.0

    @property
    def is_live(self) -> bool:
        return self.status in _LIVE_STATUSES

    @property
    def is_terminal(self) -> bool:
        return self.status in _TERMINAL_STATUSES

    def to_dict(self) -> dict[str, Any]:
        return {
            "client_order_id": self.client_order_id,
            "symbol": self.symbol,
            "price": self.price,
            "qty": self.qty,
            "side": self.side.value,
            "type": self.type.value,
            "status": self.status.value,
            "time_in_force": self.time_in_force.value,
            "reduce_only": self.reduce_only,
            "cum_exec_qty": self.cum_exec_qty,
            "cum_quote": self.cum_quote,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "Order":
        return cls(
            client_order_id=d["client_order_id"],
            symbol=d["symbol"],
            price=d["price"],
            qty=d["qty"],
            side=OrderSide(d["side"]),
            type=OrderType(d["type"]),
            time_in_force=TimeInForce(d["time_in_force"]),
            reduce_only=d["reduce_only"],
            status=OrderStatus(d["status"]),
            cum_exec_qty=d["cum_exec_qty"],
            cum_quote=d["cum_quote"],
        )


@dataclass(kw_only=True, slots=True)
class FundingRate:
    """Upcoming funding for a perp position: the rate that will be applied at `next_time`.

    Transient market data (not persisted) — refreshed periodically from premiumIndex.
    """

    symbol: str  # unified
    rate: float  # signed fraction, e.g. 0.0001 == 0.01% (long pays short when positive)
    next_time: int  # ms epoch of the next funding settlement


@dataclass(kw_only=True, slots=True)
class Position:
    symbol: str  # unified
    qty: float  # signed: positive long, negative short (one-way mode)
    entry_time: int = field(default_factory=lambda: time.time_ns() // 1_000_000)
    entry_qty: float
    cum_entry_quote: float
    cum_exit_quote: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "symbol": self.symbol,
            "qty": self.qty,
            "entry_time": self.entry_time,
            "entry_qty": self.entry_qty,
            "cum_entry_quote": self.cum_entry_quote,
            "cum_exit_quote": self.cum_exit_quote,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "Position":
        return cls(
            symbol=d["symbol"],
            qty=d["qty"],
            entry_time=d["entry_time"],
            entry_qty=d["entry_qty"],
            cum_entry_quote=d["cum_entry_quote"],
            cum_exit_quote=d["cum_exit_quote"],
        )
