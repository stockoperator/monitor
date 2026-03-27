import sys
import traceback
import os
from typing import Any
import re
import time
import gc

__re_unify_pattern: re.Pattern[str] = re.compile(r"[^A-Za-z0-9]")


def traceback_error_str() -> str:
    exc_type, exc_value, exc_tb = sys.exc_info()
    if exc_type is None or exc_value is None or exc_tb is None:
        return "No active exception"

    frames = traceback.extract_tb(exc_tb)
    call_chain: list[str] = []
    last_file = ""

    for frame in frames:
        file_name = os.path.basename(frame.filename)
        if file_name != last_file:
            call_chain.append(f"({file_name}){frame.name}")
            last_file = file_name
        else:
            call_chain.append(frame.name)

    error_line = f"line {frames[-1].lineno}: {frames[-1].line}"

    return f"{exc_type.__name__}: {exc_value}\n  {'->'.join(call_chain)}\n    {error_line}"


def validate_dict_by_dict(source: dict[str, Any], filter: dict[str, Any]) -> bool:
    """Validate dictionary. Filter dictionary: key -> value"""

    for key, value in filter.items():
        if isinstance(value, bool):
            if source[key] is not value:
                return False
        elif isinstance(value, (list, set, tuple)):
            if source[key] not in value:
                return False
        elif isinstance(value, (str, int, float)):
            if source[key] != value:
                return False
        else:
            raise NotImplementedError(f"Type {type(value).__name__} is not supported.")

    return True


_gc_state: list[tuple[float, tuple[int, int, int]]] = [(0.0, (0, 0, 0))] * 3


def gc_callback(phase: str, info: dict[str, int]) -> None:
    gen = info["generation"]

    if phase == "start":
        _gc_state[gen] = (time.perf_counter(), gc.get_count())
    elif phase == "stop":

        started_at, count_before = _gc_state[gen]
        delay = int((time.perf_counter() - started_at) * 1000)

        collected = info.get("collected", -1)
        uncollectable = info.get("uncollectable", -1)
        count_after = gc.get_count()

        if count_before[0] > 100:
            print(
                "GC "
                f"gen: {gen} "
                f"delay: {delay} ms "
                f"collected: {collected} "
                f"uncollectable: {uncollectable} "
                f"count_before: {count_before} "
                f"count_after: {count_after}"
            )
    else:
        raise ValueError("Unknown GC phase")


# gc.callbacks.append(gc_callback)
