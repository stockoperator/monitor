import hmac
import time
from typing import Any
import orjson
from aiohttp import ClientWebSocketResponse
import asyncio

from connector.connector import BaseConnector
from connector.base_classes import ExchangeName
from connector.subscription import BaseSubscription
from connector.http_client import BaseHttpClient, HTTPMethod
from connector.instrument import BaseInstrumentManager, Instrument
from connector.orderbook_service import BaseOrderbookService


class BinanceHttpClientBase(BaseHttpClient):
    def _sign(self, message: str) -> str:
        return hmac.new(key=self.secret_key.encode("utf-8"), msg=message.encode("utf-8"), digestmod="sha256").hexdigest()

    async def request(self, method: HTTPMethod, url: str, params: dict[str, Any] | None = None, is_auth_required: bool = False) -> dict[str, Any]:
        params = params if params else {}
        headers = {}

        if is_auth_required:
            headers = {"X-MBX-APIKEY": self.api_key}
            params["timestamp"] = int((time.time() - 10) * 1000)
            params["recvWindow"] = 50000

            query_str = "&".join(f"{k}={v}" for k, v in params.items())
            params["signature"] = self._sign(query_str)

        t1 = time.thread_time()
        async with self.session.request(method=method.value, url=url, params=params, headers=headers) as response:
            t2 = time.thread_time()
            r = await response.read()
            t3 = time.thread_time()
            j = orjson.loads(r)
            http_time = (t2 - t1) * 1000
            read_time = (t3 - t2) * 1000
            json_time = (time.thread_time() - t3) * 1000
            self.logger.info(f"http: {http_time:.1f} ms, read: {read_time:.1f} ms, json: {json_time:.1f}")
            return j


class BinanceBaseInstrumentManager(BaseInstrumentManager):
    def instruments_info(self, exchange_info: Any) -> list[dict[str, Any]]:
        return exchange_info["symbols"]

    def make_instrument_from_instrument_info(self, instrument_info: dict[str, Any]) -> Instrument:
        unify_symbol = instrument_info["baseAsset"] + instrument_info["quoteAsset"]

        return Instrument(
            exchange_symbol=instrument_info["symbol"],
            unified_symbol=unify_symbol,
        )


class BinanceBase(BaseConnector):
    @property
    def name(self) -> ExchangeName:
        return ExchangeName.BINANCE


class BinanceSubscription(BaseSubscription):
    def make_subscribe_message(self, channel_batch: list[str]) -> bytes:
        return orjson.dumps({"method": "SUBSCRIBE", "params": channel_batch})

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
                if ws.closed:
                    break
                await asyncio.sleep(1)  # Особенность биржи
                if ws.closed:
                    break
                await ws.send_str(message.decode("utf-8"))
                start_id = end_id
        self.logger.info("subscribe all finished")


class BinanceBaseOrderbookService(BaseOrderbookService):
    @property
    def subscription_type(self) -> type[BaseSubscription]:
        return BinanceSubscription
