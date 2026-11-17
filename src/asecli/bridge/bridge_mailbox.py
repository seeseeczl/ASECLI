"""Mailbox hygiene helpers: response ownership and outbox sweeping.

The probe validates every request; the client must equally validate the answer,
because the mailbox is a plain directory that any local process can write.
"""

from __future__ import annotations

import time
from pathlib import Path

#: Responses older than this are treated as orphans from a timed-out call.
OUTBOX_MAX_AGE = 600.0


def ownership_mismatch(response: dict, expect: dict) -> str | None:
    """Return a description of the first field that does not match, or None."""
    for key, want in expect.items():
        have = response.get(key)
        if have != want:
            return f"{key}: expected {want!r}, got {have!r}"
    return None


def sweep_outbox(outbox: Path, max_age: float = OUTBOX_MAX_AGE) -> None:
    """Drop our own responses that outlived their caller.

    A timed-out call leaves the probe still writing to ``outbox/``; those files
    accumulate and would otherwise become stale answers for a future request.
    """
    cutoff = time.time() - max_age
    try:
        entries = list(outbox.glob("req_asecli_*.json"))
    except OSError:
        return
    for entry in entries:
        try:
            if entry.stat().st_mtime < cutoff:
                entry.unlink()
        except OSError:
            continue


#: Extra polls after the deadline, so a marginally late answer is still adopted.
GRACE_POLLS = 4


def result_of(response: dict, error_type) -> str:
    """Extract the script result from a validated response envelope."""
    data = response.get("data")
    if not isinstance(data, dict):
        raise error_type("bridge response is missing its data envelope", phase="parse")
    if data.get("resultTruncated"):
        raise error_type("bridge truncated the script result; refusing partial data", phase="parse")
    if "result" not in data:
        raise error_type("bridge response carried no result", phase="parse")
    result = data["result"]
    if result is None:
        raise error_type("bridge script returned a null result", phase="command")
    if isinstance(result, str):
        return result
    import json
    return json.dumps(result, ensure_ascii=False)
