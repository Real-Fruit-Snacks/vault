from __future__ import annotations

import datetime
import re

from .basevalue import (BaseError, Duration, Link, stringify, to_number,
                        truthy, type_name)


def _as_str(v):
    if isinstance(v, str):
        return v
    raise BaseError("expected string")


def _as_list(v):
    if isinstance(v, list):
        return v
    raise BaseError("expected list")


# ---- global functions ------------------------------------------------------

def call_global(name, args, build_now):
    if name == "if":
        if not args:
            raise BaseError("if() needs a condition")
        if truthy(args[0]):
            return args[1] if len(args) > 1 else None
        return args[2] if len(args) > 2 else None
    if name == "now":
        return build_now
    if name == "today":
        return build_now.date()
    if name == "number":
        return to_number(args[0]) if args else None
    if name == "min":
        return min(to_number(a) for a in args)
    if name == "max":
        return max(to_number(a) for a in args)
    if name == "date":
        return _parse_date(args[0]) if args else None
    if name == "duration":
        return _parse_duration(args[0]) if args else None
    if name == "link":
        target = args[0].target if isinstance(args[0], Link) else stringify(args[0])
        display = stringify(args[1]) if len(args) > 1 else ""
        return Link(target, display)
    if name == "list":
        if args and isinstance(args[0], list):
            return list(args[0])
        return list(args)
    if name == "toString":
        return stringify(args[0]) if args else ""
    raise BaseError(f"unknown function {name}()")


def _parse_date(v):
    if isinstance(v, datetime.date):
        return v
    s = _as_str(v).strip()
    for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M",
                "%Y-%m-%d %H:%M", "%Y-%m-%d"):
        try:
            dt = datetime.datetime.strptime(s, fmt)
            return dt.date() if fmt == "%Y-%m-%d" else dt
        except ValueError:
            continue
    raise BaseError(f"bad date {v!r}")


_DUR_RE = re.compile(r"(-?\d+)\s*(second|minute|hour|day|week)s?", re.IGNORECASE)
_DUR_UNIT = {"second": 1, "minute": 60, "hour": 3600, "day": 86400, "week": 604800}


def _parse_duration(v):
    if isinstance(v, Duration):
        return v
    total, s = 0, _as_str(v)
    for m in _DUR_RE.finditer(s):
        total += int(m.group(1)) * _DUR_UNIT[m.group(2).lower()]
    if total == 0 and not _DUR_RE.search(s):
        raise BaseError(f"bad duration {v!r}")
    return Duration(total)


# ---- fields (.length, date parts) -----------------------------------------

_DATE_FIELDS = ("year", "month", "day", "hour", "minute", "second", "millisecond")


def get_field(recv, name):
    if name == "length":
        if isinstance(recv, (str, list)):
            return len(recv)
        raise BaseError("length on non-collection")
    if isinstance(recv, datetime.date) and name in _DATE_FIELDS:
        if name == "millisecond":
            return getattr(recv, "microsecond", 0) // 1000 if isinstance(recv, datetime.datetime) else 0
        if name in ("hour", "minute", "second") and not isinstance(recv, datetime.datetime):
            return 0
        return getattr(recv, name)
    raise BaseError(f"unknown field .{name} on {type_name(recv)}")


# ---- methods ---------------------------------------------------------------

def call_method(recv, name, args):
    tn = type_name(recv)
    if name == "toString":
        return stringify(recv)
    if name == "isEmpty":
        return not truthy(recv)
    if tn == "string":
        return _string_method(recv, name, args)
    if tn == "number":
        return _number_method(recv, name, args)
    if tn in ("date", "datetime"):
        return _date_method(recv, name, args)
    if tn == "list":
        return _list_method(recv, name, args)
    if tn == "link":
        return _link_method(recv, name, args)
    raise BaseError(f"unknown method .{name}() on {tn}")


def _string_method(s, name, args):
    if name == "contains":
        return _as_str(args[0]) in s
    if name == "containsAny":
        return any(_as_str(a) in s for a in args)
    if name == "containsAll":
        return all(_as_str(a) in s for a in args)
    if name == "startsWith":
        return s.startswith(_as_str(args[0]))
    if name == "endsWith":
        return s.endswith(_as_str(args[0]))
    if name == "lower":
        return s.lower()
    if name == "title":
        return s.title()
    if name == "trim":
        return s.strip()
    if name == "reverse":
        return s[::-1]
    if name == "repeat":
        return s * int(to_number(args[0]))
    if name == "replace":
        return s.replace(_as_str(args[0]), _as_str(args[1]))
    if name == "split":
        return s.split(_as_str(args[0])) if args else [s]
    if name == "slice":
        start = int(to_number(args[0])) if args else 0
        end = int(to_number(args[1])) if len(args) > 1 else None
        return s[start:end]
    raise BaseError(f"unknown string method .{name}()")


def _number_method(n, name, args):
    if name == "abs":
        return abs(n)
    if name == "floor":
        import math
        return math.floor(n)
    if name == "ceil":
        import math
        return math.ceil(n)
    if name == "round":
        digits = int(to_number(args[0])) if args else 0
        r = round(float(n), digits)
        return int(r) if digits <= 0 else r
    if name == "toFixed":
        digits = int(to_number(args[0])) if args else 0
        return f"{float(n):.{digits}f}"
    raise BaseError(f"unknown number method .{name}()")


def _date_method(d, name, args):
    if name == "format":
        return d.strftime(_as_str(args[0])) if args else d.isoformat()
    if name == "date":
        return d.date() if isinstance(d, datetime.datetime) else d
    if name == "time":
        return d.strftime("%H:%M:%S") if isinstance(d, datetime.datetime) else "00:00:00"
    if name == "relative":
        return d.isoformat()  # static site: no live "3 days ago"; show ISO
    raise BaseError(f"unknown date method .{name}()")


def _list_method(xs, name, args):
    if name == "contains":
        return args[0] in xs
    if name == "containsAny":
        return any(a in xs for a in args)
    if name == "containsAll":
        return all(a in xs for a in args)
    if name == "join":
        sep = _as_str(args[0]) if args else ""
        return sep.join(stringify(x) for x in xs)
    if name == "reverse":
        return list(reversed(xs))
    if name == "sort":
        try:
            return sorted(xs)
        except TypeError:
            return sorted(xs, key=stringify)
    if name == "unique":
        seen, out = set(), []
        for x in xs:
            key = stringify(x)
            if key not in seen:
                seen.add(key)
                out.append(x)
        return out
    if name == "flat":
        out = []
        for x in xs:
            out.extend(x) if isinstance(x, list) else out.append(x)
        return out
    if name == "slice":
        start = int(to_number(args[0])) if args else 0
        end = int(to_number(args[1])) if len(args) > 1 else None
        return xs[start:end]
    raise BaseError(f"unknown list method .{name}()")


def _link_method(link, name, args):
    if name == "linksTo":
        target = args[0].target if isinstance(args[0], Link) else stringify(args[0])
        return link.target == target
    raise BaseError(f"unknown link method .{name}()")
