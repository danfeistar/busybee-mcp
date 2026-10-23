"""BusyBee MCP — 通用工具函数。"""
from __future__ import annotations

from typing import Any


def dig(obj: Any, path: str, default: Any = None) -> Any:
    """按点路径安全取值，任一环节缺失返回 default。"""
    cur = obj
    for part in path.split("."):
        if cur is None:
            return default
        if isinstance(cur, dict):
            cur = cur.get(part, None)
        elif isinstance(cur, list):
            try:
                cur = cur[int(part)]
            except (ValueError, IndexError):
                return default
        else:
            return default
    return default if cur is None else cur


def first(*vals: Any, default: Any = None) -> Any:
    """返回第一个非空值（0 与空串算空，False 保留原值）。"""
    for v in vals:
        if v not in (None, "", [], {}):
            return v
    return default


def to_int(val: Any, default: int = 0) -> int:
    if isinstance(val, bool):
        return default
    if isinstance(val, (int, float)):
        return int(val)
    if isinstance(val, str):
        s = val.strip().replace(",", "").replace("+", "")
        mult = 1
        low = s.lower()
        for suf, m in (("k", 1000), ("m", 1000000), ("b", 1000000000), ("w", 10000), ("万", 10000), ("亿", 100000000)):
            if low.endswith(suf):
                mult, s = m, s[: -len(suf)]
                break
        try:
            return int(float(s) * mult)
        except ValueError:
            return default
    return default


def truncate(text: Any, limit: int = 1200) -> str:
    s = "" if text is None else str(text)
    return s if len(s) <= limit else s[: limit - 1] + "…"


def unix_to_iso(ts: Any) -> str | None:
    import datetime as _dt

    n = to_int(ts, 0)
    if n <= 0:
        return None
    if n > 10**12:  # 毫秒
        n //= 1000
    try:
        return _dt.datetime.fromtimestamp(n, _dt.timezone.utc).isoformat()
    except (OSError, ValueError):
        return None
