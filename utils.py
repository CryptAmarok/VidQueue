import ast
import math
from typing import Any, Generator


def _parse_value(value: str) -> Any:
    try:
        return ast.literal_eval(value)
    except (ValueError, SyntaxError):
        return value


def parse_kwargs(kwlist: list) -> dict[str, Any]:
    """Parse a list of 'key=value' strings into a dict.
    Example: ['crf=24', 'preset=fast'] -> {'crf': 24, 'preset': 'fast'}
    """
    return {
        key: _parse_value(value)
        for arg in kwlist
        for key, value in [arg.split('=', 1)]
    }


def show_list(files: list) -> Generator[str, None, None]:
    list_length = len(files)
    zeros = int(math.log10(list_length)) + 2 if list_length > 0 else 1
    for index, value in enumerate(files):
        yield f'{(str(index + 1) + "."):>{zeros}} - {value}'
