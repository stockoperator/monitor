import sys
import traceback
import os
from typing import Any
import re

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
