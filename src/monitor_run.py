import asyncio
from typing import Type
import os
import uvloop


from connector.binance.binance_perp import BinancePerp
from connector.binance.binance_spot import BinanceSpot
from connector.connector import BaseConnector
from connector.monitor import Monitor

asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())


if __name__ == "__main__":
    print(f"PID: {os.getpid()}")
    connector_type_list: list[Type[BaseConnector]] = [BinancePerp, BinanceSpot]
    m = Monitor(connector_type_list=connector_type_list)
    # gc.disable()
    asyncio.run(m.run())
