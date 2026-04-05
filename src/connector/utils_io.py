import pickle
import asyncio
import numpy as np
from typing import Type, Any

from connector.connector import BaseConnector


def save_all_trade_data_sync(connectors: dict[Type[BaseConnector], BaseConnector], path: str):
    data: dict[str, Any] = {}
    for connector_type, connector in connectors.items():
        data[connector_type.__name__] = {}

        for instrument in connector.instrument_manager.values():
            trade_container = connector.trade_service[instrument.exchange_symbol]  # has default
            container_data = {}

            for trade_container_attr in ("public_trades", "public_trades_1s", "public_trades_1m", "public_trades_1h", "public_side_trades"):
                if hasattr(trade_container, trade_container_attr):
                    public_trades = getattr(trade_container, trade_container_attr)
                    public_trades_data = {}

                    for public_trade_attr in ("size", "idx", "wrapped", "timestamps", "prices", "volumes", "open_prices", "close_prices", "delta_volumes"):
                        if hasattr(public_trades, public_trade_attr):
                            public_trades_data[public_trade_attr] = getattr(public_trades, public_trade_attr)

                    container_data[trade_container_attr] = public_trades_data

            data[connector_type.__name__][instrument.exchange_symbol] = container_data

    with open(path, "wb") as f:
        pickle.dump(data, f, protocol=pickle.HIGHEST_PROTOCOL)


async def save_all_trade_data(connectors: dict[Type[BaseConnector], BaseConnector], path: str = "all_trade_containers.pkl"):
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, save_all_trade_data_sync, connectors, path)


def load_all_trade_data_sync(connectors: dict[Type[BaseConnector], BaseConnector], path: str):
    with open(path, "rb") as f:
        data = pickle.load(f)

    for connector_type, connector in connectors.items():
        for symbol, trade_container_data in data.get(connector_type.__name__, {}).items():
            trade_container = connector.trade_service[symbol]  # has default

            for trade_container_attr, public_trades_data in trade_container_data.items():
                if hasattr(trade_container, trade_container_attr):
                    public_trades = getattr(trade_container, trade_container_attr)

                    for public_trade_attr, value in public_trades_data.items():
                        if hasattr(public_trades, public_trade_attr):
                            public_trades_variable = getattr(public_trades, public_trade_attr)

                            if isinstance(public_trades_variable, np.ndarray) and isinstance(value, np.ndarray):
                                public_trades_variable[:] = value
                            else:
                                setattr(public_trades, public_trade_attr, value)


async def load_all_trade_data(connectors: dict[Type[BaseConnector], BaseConnector], path: str = "all_trade_containers.pkl"):
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, load_all_trade_data_sync, connectors, path)
