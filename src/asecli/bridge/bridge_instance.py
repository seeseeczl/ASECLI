"""DSH-Bridge instance record: discovery, ownership and liveness.

The record lives at ``Library/DSHBridge/instance.json``.  It is a plain file, so
it can be copied or planted; ownership is therefore re-checked against the
requested project, and a future-dated heartbeat is treated as unhealthy rather
than perpetually fresh.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

BRIDGE_ROOT = Path("Library") / "DSHBridge"
#: Tolerated clock skew before a future ``lastSeenAt`` counts as unhealthy.
CLOCK_SKEW_TOLERANCE = 60.0


def _instance_path(project_root: Path) -> Path:
    return project_root / BRIDGE_ROOT / "instance.json"


def read_instance(project_root: Path) -> dict | None:
    """Return the bridge instance record for *project_root*, or None.

    A record is accepted only when it describes this project: the mailbox is a
    plain directory, so a copied or stale file must never steer a call into
    another editor.
    """
    candidate = _instance_path(project_root)
    try:
        if not candidate.is_file():
            return None
        data = json.loads(candidate.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(data, dict):
        return None
    declared = data.get("projectPath")
    if isinstance(declared, str) and declared:
        if Path(declared).resolve() != project_root.resolve():
            return None
    for key in ("instanceId", "bootId", "nonce"):
        if not isinstance(data.get(key), str) or not data[key]:
            return None
    return data


def instance_is_stale(instance: dict, *, now: float | None = None) -> bool:
    """True when the bridge heartbeat has lapsed past its declared threshold."""
    last = instance.get("lastSeenAt")
    if not isinstance(last, str):
        return False
    threshold_ms = instance.get("staleAfterMs")
    if not isinstance(threshold_ms, (int, float)) or threshold_ms <= 0:
        return False
    try:
        stamp = time.mktime(time.strptime(last[:19], "%Y-%m-%dT%H:%M:%S"))
    except ValueError:
        return False
    # instance.json is written in UTC.
    stamp -= time.timezone if not time.daylight else time.altzone
    current = time.time() if now is None else now
    return (current - stamp) * 1000 > threshold_ms



def _parse_heartbeat(last: str) -> float | None:
    """Convert an ISO-8601 UTC stamp to a POSIX timestamp."""
    try:
        stamp = time.mktime(time.strptime(last[:19], "%Y-%m-%dT%H:%M:%S"))
    except ValueError:
        return None
    return stamp - (time.timezone if not time.daylight else time.altzone)


def instance_is_stale(instance: dict, *, now: float | None = None) -> bool:
    """True when the heartbeat lapsed, or is dated implausibly far ahead."""
    last = instance.get("lastSeenAt")
    threshold_ms = instance.get("staleAfterMs")
    if not isinstance(last, str) or not isinstance(threshold_ms, (int, float)) or threshold_ms <= 0:
        return False
    stamp = _parse_heartbeat(last)
    if stamp is None:
        return False
    age = (time.time() if now is None else now) - stamp
    if age < -CLOCK_SKEW_TOLERANCE:
        # A heartbeat from the future means the clock moved; the instance cannot
        # be trusted to be alive (AA-DATA-021).
        return True
    return age * 1000 > threshold_ms
