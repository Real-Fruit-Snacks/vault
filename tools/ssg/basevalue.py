from __future__ import annotations

import datetime
from dataclasses import dataclass


class BaseError(Exception):
    """Any unsupported/failed base operation. The evaluator catches it and
    yields null (empty cell / false filter) plus a one-time warning."""


@dataclass(frozen=True)
class Link:
    target: str
    display: str = ""


@dataclass(frozen=True)
class Duration:
    seconds: float


def type_name(v) -> str:
    if v is None:
        return "null"
    if isinstance(v, bool):
        return "boolean"
    if isinstance(v, (int, float)):
        return "number"
    if isinstance(v, str):
        return "string"
    if isinstance(v, list):
        return "list"
    if isinstance(v, Link):
        return "link"
    if isinstance(v, Duration):
        return "duration"
    if isinstance(v, datetime.datetime):
        return "datetime"
    if isinstance(v, datetime.date):
        return "date"
    return "object"


def truthy(v) -> bool:
    if v is None or v is False:
        return False
    if isinstance(v, bool):
        return v
    if isinstance(v, (int, float)):
        return v != 0
    if isinstance(v, str):
        return v.strip() != ""
    if isinstance(v, list):
        return len(v) > 0
    return True


def to_number(v):
    if isinstance(v, bool):
        raise BaseError("boolean is not a number")
    if isinstance(v, (int, float)):
        return v
    if isinstance(v, str):
        s = v.strip()
        try:
            return float(s) if ("." in s or "e" in s.lower()) else int(s)
        except ValueError:
            raise BaseError(f"not a number: {v!r}")
    raise BaseError(f"not a number: {type_name(v)}")


def stringify(v) -> str:
    if v is None:
        return ""
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, Link):
        return v.display or v.target
    if isinstance(v, datetime.datetime):
        return v.isoformat(sep=" ")
    if isinstance(v, datetime.date):
        return v.isoformat()
    if isinstance(v, list):
        return ", ".join(stringify(x) for x in v)
    return str(v)


def _is_date(v):
    return isinstance(v, datetime.date)  # datetime is a subclass


def binary(op: str, a, b):
    if op == "+":
        if isinstance(a, str) or isinstance(b, str):
            return stringify(a) + stringify(b)
        if _is_date(a) and isinstance(b, Duration):
            return a + datetime.timedelta(seconds=b.seconds)
        if isinstance(a, Duration) and _is_date(b):
            return b + datetime.timedelta(seconds=a.seconds)
        return to_number(a) + to_number(b)
    if op == "-":
        if _is_date(a) and isinstance(b, Duration):
            return a - datetime.timedelta(seconds=b.seconds)
        return to_number(a) - to_number(b)
    if op in ("*", "/", "%"):
        x, y = to_number(a), to_number(b)
        if op == "*":
            return x * y
        if y == 0:
            raise BaseError("division by zero")
        return x / y if op == "/" else x % y
    raise BaseError(f"unknown operator {op!r}")


_ORDER = {">", "<", ">=", "<="}


def compare(op: str, a, b) -> bool:
    if op == "==":
        return a == b and type_name(a) == type_name(b)
    if op == "!=":
        return not (a == b and type_name(a) == type_name(b))
    if op not in _ORDER:
        raise BaseError(f"unknown comparison {op!r}")
    # Ordering only between matching, orderable types.
    if isinstance(a, bool) or isinstance(b, bool):
        return False
    num = isinstance(a, (int, float)) and isinstance(b, (int, float))
    txt = isinstance(a, str) and isinstance(b, str)
    dat = _is_date(a) and _is_date(b)
    if not (num or txt or dat):
        return False
    if dat:  # normalize date vs datetime for comparison
        a = a if isinstance(a, datetime.datetime) else datetime.datetime(a.year, a.month, a.day)
        b = b if isinstance(b, datetime.datetime) else datetime.datetime(b.year, b.month, b.day)
    if op == ">":
        return a > b
    if op == "<":
        return a < b
    if op == ">=":
        return a >= b
    return a <= b
