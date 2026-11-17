"""Codely Bridge readiness probe.

Kept apart from the client so the transport stays about framing, and so the
probe can evolve (extra capability checks) without growing the wire code.
"""

from __future__ import annotations

import time
from pathlib import Path

from .codely_client import CodelyClient, CodelyError

PROBE_SCRIPT = 'return "asecli-probe-ok";'

#: Optional capability check: an editor that answers but cannot load ASE would
#: otherwise look healthy until the first real shader operation fails.
ASE_CHECK = (
    'var t = System.AppDomain.CurrentDomain.GetAssemblies()'
    '.Select(a => a.GetType("AmplifyShaderEditor.AmplifyShaderEditorWindow"))'
    '.FirstOrDefault(x => x != null); return t == null ? "ase-missing" : "ase-present";'
)


def probe(project_root: str | Path | None = None, *, port: int | None = None,
          timeout: float = 30.0, check_ase: bool = False) -> dict:
    """Connect, handshake and run a trivial script; never raises."""
    started = time.monotonic()
    reason = None
    details: dict = {}
    try:
        client = CodelyClient(project_root, port=port, timeout=timeout)
        try:
            info = client.connect()
            value = client.execute_code(PROBE_SCRIPT)
            details = {"handshake": info.get("handshake"), "probe_value": value}
            ok = "asecli-probe-ok" in value
            if not ok:
                reason = f"probe returned unexpected value: {value[:80]}"
            if check_ase:
                details["ase_available"] = "ase-present" in client.execute_code(ASE_CHECK)
        finally:
            client.close()
    except CodelyError as exc:
        ok = False
        reason = f"{exc.phase or 'error'}: {exc}"
        details = exc.data
    except Exception as exc:  # defensive: probe must not raise
        ok = False
        reason = f"{type(exc).__name__}: {exc}"
    return {
        "ok": ok,
        "port": port if port is not None else details.get("port"),
        "reason": reason,
        "elapsed_ms": round((time.monotonic() - started) * 1000),
        **details,
    }
