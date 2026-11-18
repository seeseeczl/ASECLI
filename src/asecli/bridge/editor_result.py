"""Normalise a script payload out of either backend's response text.

mcp-for-unity wraps results in ``{"success":..,"data":{<key>:..}}`` while Codely
returns the bare string the script produced, so both funnel through here and
call sites only ever see one shape.
"""

from __future__ import annotations

import json

RESULT_KEYS = ("result", "output", "value", "text")


class EditorExecutionError(RuntimeError):
    """Raised when the editor reports a failed execution envelope."""

    def __init__(self, message: str, *, data: dict | None = None):
        super().__init__(message)
        self.data = data or {}


def _unwrap_codely(text: str) -> str:
    """Strip the JSON string quoting Codely puts around a script's return value."""
    stripped = text.strip()
    if not (stripped.startswith('"') and stripped.endswith('"')):
        return text
    try:
        parsed = json.loads(stripped)
    except json.JSONDecodeError:
        return text
    return parsed if isinstance(parsed, str) else text


#: Transports that hand back the script's own string, with no JSON envelope.
RAW_PAYLOAD_BACKENDS = frozenset({"bridge", "codely", "raw"})


def extract_payload(text: str, backend: str) -> str:
    """Return the script's own payload from a backend's response text."""
    if backend != "mcp" and backend not in RAW_PAYLOAD_BACKENDS:
        raise ValueError(f"unknown backend {backend!r} for payload extraction")
    if backend in RAW_PAYLOAD_BACKENDS:
        return _unwrap_codely(text)
    try:
        envelope = json.loads(text.strip())
    except json.JSONDecodeError:
        return text
    if not isinstance(envelope, dict):
        return text
    if envelope.get("success") is False:
        data = envelope.get("data") if isinstance(envelope.get("data"), dict) else {}
        detail = envelope.get("message") or data.get("reason") or "editor execution failed"
        available = data.get("available_instances")
        if isinstance(available, list) and available:
            detail = f"{detail}; available instances: {', '.join(str(item) for item in available)}"
        raise EditorExecutionError(str(detail), data=data)
    data = envelope.get("data")
    if isinstance(data, dict):
        # Probe by shape rather than pinning one server's key name.
        for key in RESULT_KEYS:
            payload = data.get(key)
            if isinstance(payload, str):
                if payload.strip():
                    return payload
                raise EditorExecutionError(
                    f"editor returned an empty {key!r} payload", data=data
                )
    raise EditorExecutionError(
        "editor response carried no recognisable payload "
        f"(data keys: {sorted(data) if isinstance(data, dict) else 'none'})",
        data=data if isinstance(data, dict) else {},
    )
