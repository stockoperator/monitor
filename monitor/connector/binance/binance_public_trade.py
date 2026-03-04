import orjson
import asyncio
from typing import Any, Type
from aiohttp import ClientWebSocketResponse

from connector.events import PublicTradeEvent
from connector.public_trade_service import BasePublicTradeService
from connector.data_parser import BaseDataParser
from connector.base_classes import PublicTrade


class BinancePublicTradeDataParser(BaseDataParser):
    def _parse_public_trade(self, data: dict[str, Any]) -> PublicTrade:
        return PublicTrade(
            symbol=str(data["s"]),
            exchange_ts_ms=int(data["T"]),
            transaction_ts_ms=int(data["E"]),
            trade_id=str(data["a"]),
            price=float(data["p"]),
            amount=float(data["q"]),
            buy=not data["m"],
        )

    async def route_message(self, data: dict[str, Any]) -> None:
        event_type = data.get("e", "")

        if event_type == "aggTrade":
            public_trade = self._parse_public_trade(data)
            self.on_event(PublicTradeEvent(public_trade))


class BinancePublicTradeService(BasePublicTradeService):
    @property
    def data_parser_type(self) -> Type[BaseDataParser]:
        return BinancePublicTradeDataParser

    def make_subscribe_message(self, channel_batch: list[str]) -> bytes:
        return orjson.dumps({"method": "SUBSCRIBE", "params": channel_batch})

    def get_channel(self, symbol: str) -> str:
        return f"{symbol.lower()}@aggTrade"

    async def subscribe_channels(self, ws: ClientWebSocketResponse, channels: list[str], bytes_per_ws_message: int = 1000) -> None:
        channel_len = len(orjson.dumps(channels[0])) + 1
        non_channel_len = len(self.make_subscribe_message(channels[0:1])) - channel_len + 1
        batch_size = int(0.9 * (bytes_per_ws_message - non_channel_len) // channel_len)

        start_id: int = 0

        while start_id < len(channels):
            end_id: int = min(len(channels), start_id + batch_size)  # end_id not included!
            if start_id >= end_id:
                raise ValueError("start_id >= end_id")
            message = self.make_subscribe_message(channels[start_id:end_id])
            if len(message) > bytes_per_ws_message:
                batch_size -= 1
            else:
                if ws.closed or self.websocket_manager.ws != ws:
                    break
                await asyncio.sleep(1)  # Особенность биржи
                if ws.closed or self.websocket_manager.ws != ws:
                    break
                await ws.send_str(message.decode("utf-8"))
                start_id = end_id
        self.logger.info("subscribe all finished")
