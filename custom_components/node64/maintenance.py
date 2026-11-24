import re
from datetime import datetime, timezone
from typing import Any

_ZERO_PREFIX = "0001-01-01"
_FRACTION = re.compile(r"(\.\d{6})\d+")


def _parse(value: str | None) -> datetime | None:
    if not value or value.startswith(_ZERO_PREFIX):
        return None
    try:
        return datetime.fromisoformat(_FRACTION.sub(r"\1", value.replace("Z", "+00:00")))
    except ValueError:
        return None


def _iso(value: str | None) -> str | None:
    return value if _parse(value) else None


def _hc_window_active(window: dict[str, Any], now: datetime) -> bool:
    if not window.get("active"):
        return False
    start = _parse(window.get("start_at"))
    if start and now < start:
        return False
    end = _parse(window.get("end_at"))
    return not (end and now >= end and not window.get("repeat"))


def hc_maintenance_for(data: dict[str, Any], token: str) -> tuple[str | None, str | None]:
    now = datetime.now(timezone.utc)
    for window in _dicts(data.get("hc_windows")):
        if token in (window.get("tokens") or []) and _hc_window_active(window, now):
            until = None if window.get("repeat") else _iso(window.get("end_at"))
            return until, window.get("name")
    return None, None


def _dicts(items: Any) -> list[dict[str, Any]]:
    return [item for item in items or [] if isinstance(item, dict)]


def m64_windows(data: dict[str, Any]) -> list[dict[str, Any]]:
    return _dicts((data.get("m64") or {}).get("windows"))


def m64_host_maintenance(
    host: dict[str, Any], windows: list[dict[str, Any]], uid: str
) -> tuple[bool, str | None, str | None]:
    maint = host.get("maint")
    if maint is None:
        return False, None, None
    until = _iso(maint.get("end"))
    reason = maint.get("reason") or None
    if until is None:
        for window in windows:
            if not window.get("running") or _iso(window.get("end")) is None:
                continue
            if (
                uid in (window.get("hosts") or [])
                or (host.get("group") and host["group"] in (window.get("groups") or []))
                or any(tag in (window.get("tags") or []) for tag in host.get("tags") or [])
            ):
                until = _iso(window.get("end"))
                reason = reason or window.get("title")
                break
    return True, until, reason


def maintenance_windows(data: dict[str, Any]) -> list[dict[str, Any]]:
    now = datetime.now(timezone.utc)
    m64 = data.get("m64") or {}
    hosts = m64.get("hosts") or {}
    windows: list[dict[str, Any]] = []

    for window in m64_windows(data):
        if not window.get("running"):
            continue
        if window.get("hosts"):
            scope = "host"
            targets = [hosts.get(uid, {}).get("name", uid) for uid in window["hosts"]]
        elif window.get("groups"):
            scope = "group"
            targets = list(window["groups"])
        else:
            scope = "tag"
            targets = list(window.get("tags") or [])
        windows.append(
            {
                "name": window.get("title"),
                "scope": scope,
                "targets": targets,
                "start": _iso(window.get("start")),
                "end": _iso(window.get("end")),
                "reason": window.get("title"),
            }
        )

    checks = data.get("checks") or {}
    for window in _dicts(data.get("hc_windows")):
        if not _hc_window_active(window, now):
            continue
        windows.append(
            {
                "name": window.get("name"),
                "scope": "check",
                "targets": [checks.get(token, {}).get("name", token) for token in window.get("tokens") or []],
                "start": _iso(window.get("start_at")),
                "end": _iso(window.get("end_at")),
                "reason": window.get("name"),
            }
        )
    return windows
