"""Shared fixtures for the DSH-Bridge transport tests.

A fake mailbox stands in for the editor so the protocol can be exercised
without a live bridge.
"""

from __future__ import annotations

import json
import threading
import time

import pytest

NONCE = "0123456789abcdef0123456789abcdef"


@pytest.fixture
def project(tmp_path):
    root = tmp_path / "Project"
    (root / "Assets").mkdir(parents=True)
    (root / "ProjectSettings").mkdir()
    return root


def write_instance(project, *, boot="boot01", pid=4242, stale_after=6000):
    record = {
        "v": 1,
        "discoveryVersion": 1,
        "instanceId": "unity:abc123",
        "bootId": boot,
        "nonce": NONCE,
        "pid": pid,
        "projectPath": str(project),
        "probeVersion": "8",
        "staleAfterMs": stale_after,
        "heartbeatIntervalMs": 2000,
        "lastSeenAt": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    base = project / "Library" / "DSHBridge"
    (base / boot / "inbox").mkdir(parents=True, exist_ok=True)
    (base / boot / "outbox").mkdir(parents=True, exist_ok=True)
    (base / boot / "done").mkdir(parents=True, exist_ok=True)
    (base / "instance.json").write_text(json.dumps(record), encoding="utf-8")
    return record


class FakeEditor(threading.Thread):
    """Consumes inbox requests and answers via outbox, like the real probe."""

    def __init__(self, project, responder):
        super().__init__(daemon=True)
        self.inbox = project / "Library" / "DSHBridge" / "boot01" / "inbox"
        self.outbox = project / "Library" / "DSHBridge" / "boot01" / "outbox"
        self.responder = responder
        self.requests: list[dict] = []
        self._stop = False

    def run(self):
        while not self._stop:
            for path in sorted(self.inbox.glob("*.json")):
                request = json.loads(path.read_text())
                self.requests.append(request)
                answer = self.responder(request)
                if answer is not None:
                    (self.outbox / path.name).write_text(json.dumps(answer))
                path.unlink()
            time.sleep(0.01)

    def stop(self):
        self._stop = True


def _envelope(request, **overrides):
    """A response carrying the ownership fields a real probe echoes back."""
    base = {
        "v": 1,
        "id": request["id"],
        "instanceId": request.get("instanceId"),
        "bootId": request.get("bootId"),
        "nonce": request.get("nonce"),
        "ok": True,
    }
    base.update(overrides)
    return base


def ok_answer(value):
    def responder(request):
        return _envelope(request, data={"result": value, "resultTruncated": False,
                                        "backend": "mono-mcs"})
    return responder


