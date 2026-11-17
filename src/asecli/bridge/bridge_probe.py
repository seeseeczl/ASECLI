"""DSH-Bridge readiness probe and instance discovery checks.

Split from the mailbox client so the transport stays about framing and the
probe can grow (capability reporting) without touching the wire code.
"""

from __future__ import annotations

import time
from pathlib import Path

from .bridge_client import BridgeClient, BridgeError, instance_is_stale, read_instance

PROBE_SCRIPT = 'return "asecli-probe-ok";'
#: Surfaced so callers can show what this transport is allowed to do.
CAPABILITY_LEVEL = "unrestricted-code"


def probe(project_root: str | Path, *, timeout: float = 30.0) -> dict:
    """Check the bridge answers; never raises."""
    started = time.monotonic()
    try:
        instance = read_instance(Path(project_root))
        if instance is None:
            return {"ok": False, "reason": "no DSH-Bridge instance for this project", "elapsed_ms": 0}
        if instance_is_stale(instance):
            return {"ok": False, "reason": "bridge heartbeat is stale", "elapsed_ms": 0}
        client = BridgeClient(project_root, timeout=timeout)
        try:
            client.connect()
            value = client.execute_code('return "asecli-probe-ok";')
        finally:
            client.close()
        ok = "asecli-probe-ok" in value
        return {
            "ok": ok,
            "reason": None if ok else f"probe returned {value[:80]!r}",
            "instance_id": instance.get("instanceId"),
            "probe_version": instance.get("probeVersion"),
            # This transport runs arbitrary C# with the editor's own rights and
            # is not gated by the bridge's dangerous-capability allow-list.
            "capability_level": CAPABILITY_LEVEL,
            "elapsed_ms": round((time.monotonic() - started) * 1000),
        }
    except BridgeError as exc:
        return {"ok": False, "reason": f"{exc.phase or 'error'}: {exc}", "elapsed_ms": round((time.monotonic() - started) * 1000)}
    except Exception as exc:  # defensive: probing must not raise
        return {"ok": False, "reason": f"{type(exc).__name__}: {exc}", "elapsed_ms": round((time.monotonic() - started) * 1000)}
