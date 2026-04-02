import pickle
import asyncio
from typing import Type, Any

from connector.connector import BaseConnector


def save_all_trade_data_sync(connectors_dict: dict[Type[BaseConnector], BaseConnector], path: str):
    data: dict[str, Any] = {}
    for connector_type, connector in connectors_dict.items():
        data[connector_type.__name__] = {}
        for symbol, container in connector.trade_service.containers.items():
            series_dict = {}
            for attr in ("public_trades", "public_trades_1s", "public_trades_1m", "public_trades_1h"):
                series = getattr(container, attr)
                s_data = {
                    "size": series.size,
                    "idx": series.idx,
                    "timestamps": series.timestamps.copy(),
                    "prices": series.prices.copy(),
                    "volumes": series.volumes.copy(),
                }
                if hasattr(series, "delta_volumes"):
                    s_data["delta_volumes"] = series.delta_volumes.copy()
                series_dict[attr] = s_data
            data[connector_type.__name__][symbol] = series_dict

    with open(path, "wb") as f:
        pickle.dump(data, f, protocol=pickle.HIGHEST_PROTOCOL)


async def save_all_trade_data(connectors_dict: dict[Type[BaseConnector], BaseConnector], path: str = "all_trade_containers.pkl"):
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, save_all_trade_data_sync, connectors_dict, path)


def load_all_trade_data_sync(connectors_dict: dict[Type[BaseConnector], BaseConnector], path: str):
    with open(path, "rb") as f:
        saved_data = pickle.load(f)

    connector_by_name = {cls.__name__: conn for cls, conn in connectors_dict.items()}

    for connector_name, symbols_dict in saved_data.items():
        connector = connector_by_name.get(connector_name)
        if not connector:
            continue
        for symbol, series_dict in symbols_dict.items():
            container = connector.trade_service[symbol]
            if not container:
                continue
            for attr, s_data in series_dict.items():
                series = getattr(container, attr)
                series.size = s_data["size"]
                series.idx = s_data["idx"]
                series.timestamps[:] = s_data["timestamps"]
                series.prices[:] = s_data["prices"]
                series.volumes[:] = s_data["volumes"]
                if hasattr(series, "delta_volumes") and "delta_volumes" in s_data:
                    series.delta_volumes[:] = s_data["delta_volumes"]


async def load_all_trade_data(connectors_dict: dict[Type[BaseConnector], BaseConnector], path: str = "all_trade_containers.pkl"):
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, load_all_trade_data_sync, connectors_dict, path)
