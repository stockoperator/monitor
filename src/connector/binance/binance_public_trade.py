import orjson
from typing import Any
import time

from connector.subscription import BaseSubscription
from connector.public_trade_service import BasePublicTradeService
from connector.binance.binance_base import BinanceSubscription


class BinancePublicTradeService(BasePublicTradeService):
    @property
    def subscription_type(self) -> type[BaseSubscription]:
        return BinanceSubscription

    def get_channel(self, symbol: str) -> str:
        return f"{symbol.lower()}@aggTrade"

    def handle_message(self, message: str) -> None:
        data: dict[str, Any] = orjson.loads(message)
        event_type = data.get("e", "")

        if event_type == "aggTrade":
            symbol = str(data["s"])
            transaction_ts_ms = int(data["E"])
            price = float(data["p"])
            amount = float(data["q"])
            is_buy = not data["m"]

            public_trades = self[symbol]

            t0 = time.perf_counter_ns()
            tt0 = time.thread_time_ns()
            public_trades.add(transaction_ts_ms, price, amount, is_buy)
            wall_ms = (time.perf_counter_ns() - t0) / 1e6
            thread_ms = (time.thread_time_ns() - tt0) / 1e6

            if wall_ms >= 2:
                self.logger.info("append wall=%.1f ms thread=%.1f", wall_ms, thread_ms)
