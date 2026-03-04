import orjson
import asyncio
from aiohttp import ClientWebSocketResponse
from typing import Any

from connector.orderbook_service import BaseOrderbookService
from connector.data_parser import BaseDataParser
from connector.base_classes import PriceLevel


class BinanceOrderbookDataParser(BaseDataParser):
    def _parse_price_levels(self, raw_levels: Any) -> list[PriceLevel]:
        result: list[PriceLevel] = []
        for price, amount in raw_levels:
            result.append(PriceLevel(price=float(price), amount=float(amount)))
        return result


class BinanceOrderbookService(BaseOrderbookService):
    def make_subscribe_message(self, channel_batch: list[str]) -> bytes:
        return orjson.dumps({"method": "SUBSCRIBE", "params": channel_batch})

    def get_channel(self, symbol: str) -> str:
        return f"{symbol.lower()}@depth@100ms"

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
                self.logger.info(
                    f"subscribe start_id: {start_id} finished. "
                    f"queues: data={self.data_events.qsize()}, "
                    f"event={self.events.qsize()}, "
                    f"parser={self.data_parser.events.qsize()}"
                )
                start_id = end_id
        self.logger.info("subscribe all finished")
