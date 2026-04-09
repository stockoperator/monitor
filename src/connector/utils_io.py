import pickle
import asyncio
import numpy as np
from typing import Type, Any, cast

from connector.connector import BaseConnector


def get_all_slot_attrs(obj: object) -> set[str]:
    attrs: set[str] = set()

    for cls in type(obj).__mro__:
        slots = getattr(cls, "__slots__", ())

        if isinstance(slots, tuple):
            for slot_attr in cast(tuple[str, ...], slots):
                attrs.add(slot_attr)

    return attrs


async def save_all_trade_data(connectors: dict[Type[BaseConnector], BaseConnector], path: str = "all_trade_containers.pkl"):
    def _dump_pickle(path: str, data: dict[str, Any]) -> None:
        with open(path, "wb") as f:
            pickle.dump(data, f, protocol=pickle.HIGHEST_PROTOCOL)

    data: dict[str, Any] = {}
    for connector_type, connector in connectors.items():
        data[connector_type.__name__] = {}

        for instrument in connector.instrument_manager.values():
            trade_container = connector.trade_service[instrument.exchange_symbol]  # has default
            container_data = {}

            for trade_container_attr in trade_container.__slots__:
                public_trades = getattr(trade_container, trade_container_attr)
                public_trades_data = {}

                for public_trade_attr in get_all_slot_attrs(public_trades):
                    public_trades_data[public_trade_attr] = getattr(public_trades, public_trade_attr)

                container_data[trade_container_attr] = public_trades_data

            data[connector_type.__name__][instrument.exchange_symbol] = container_data

            await asyncio.sleep(0)

    await asyncio.to_thread(_dump_pickle, path, data)


async def load_all_trade_data(connectors: dict[Type[BaseConnector], BaseConnector], path: str = "all_trade_containers.pkl"):
    def _load_pickle(path: str) -> dict[str, Any]:
        with open(path, "rb") as f:
            return pickle.load(f)

    data = await asyncio.to_thread(_load_pickle, path)

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

            await asyncio.sleep(0)
