"""Adversarial regression tests for the DSH-Bridge transport.

Every case here plants something in the mailbox that a well-behaved probe would
never create, because those are the paths ordinary testing misses.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import time

import pytest

from asecli.bridge.bridge_client import BridgeClient, BridgeError, instance_is_stale
from asecli.bridge.bridge_probe import probe

from tests._bridge_harness import (  # noqa: F401  (fixtures re-exported for pytest)
    NONCE, FakeEditor, _envelope, ok_answer, project, write_instance,
)




def test_planted_response_with_wrong_owner_is_refused(project):
    """AA-OPT-020: a file planted in outbox must not become our answer."""
    write_instance(project)
    outbox = project / "Library" / "DSHBridge" / "boot01" / "outbox"

    def plant(request):
        # Same id, another session's identity: the answer must not be adopted.
        (outbox / f"{request['id']}.json").write_text(json.dumps(
            {"v": 1, "id": request["id"], "instanceId": "unity:impostor",
             "bootId": "boot01", "nonce": NONCE, "ok": True,
             "data": {"result": "POISON", "resultTruncated": False}}))
        return None

    editor = FakeEditor(project, plant)
    editor.start()
    try:
        with BridgeClient(project, timeout=10) as client:
            with pytest.raises(BridgeError) as excinfo:
                client.execute_code("return 1;")
    finally:
        editor.stop()
    assert excinfo.value.phase == "protocol"
    assert "instanceId" in str(excinfo.value)


def test_future_heartbeat_is_treated_as_stale(project):
    """AA-OPT-021: a heartbeat dated far ahead must not look healthy."""
    record = write_instance(project)
    ahead = dict(record, lastSeenAt="2099-01-01T00:00:00Z")
    assert instance_is_stale(ahead) is True
    # Small skew is tolerated.
    near = dict(record, lastSeenAt=time.strftime(
        "%Y-%m-%dT%H:%M:%SZ", time.gmtime(time.time() + 5)))
    assert instance_is_stale(near) is False


def test_timeout_leaves_no_outbox_orphan(project):
    """AA-OPT-023: a timed-out call must not leave its response behind."""
    write_instance(project)
    outbox = project / "Library" / "DSHBridge" / "boot01" / "outbox"
    editor = FakeEditor(project, lambda r: None)  # never answers
    editor.start()
    try:
        with BridgeClient(project, timeout=0.3) as client:
            with pytest.raises(BridgeError, match="timed out"):
                client.execute_code("return 1;")
    finally:
        editor.stop()
    assert list(outbox.glob("req_asecli_*.json")) == []


def test_old_outbox_orphans_are_swept(project):
    """AA-OPT-023: stale responses from earlier calls are reclaimed."""
    write_instance(project)
    outbox = project / "Library" / "DSHBridge" / "boot01" / "outbox"
    orphan = outbox / "req_asecli_deadbeefdeadbeef.json"
    orphan.write_text("{}")
    old = time.time() - 3600
    os.utime(orphan, (old, old))

    editor = FakeEditor(project, ok_answer("fresh"))
    editor.start()
    try:
        with BridgeClient(project, timeout=5) as client:
            client.execute_code("return 1;")
    finally:
        editor.stop()
    assert not orphan.exists()


def test_cache_key_separates_credentials(project, monkeypatch):
    """AA-OPT-022: different instance tokens must not share a decision."""
    from asecli.bridge import backend as backend_module

    monkeypatch.setattr(backend_module, "probe_mcp", lambda *a, **k: {"ok": True, "reason": None})
    monkeypatch.setattr(backend_module, "bridge_probe", lambda r, **k: {"ok": False, "reason": "no"})
    monkeypatch.setattr(backend_module, "codely_probe", lambda r, **k: {"ok": False, "reason": "no"})
    backend_module.clear_backend_cache()
    try:
        backend_module.select_backend("auto", project, instance_token="A")
        backend_module.select_backend("auto", project, instance_token="B")
        assert len(backend_module._choice_cache) == 2
    finally:
        backend_module.clear_backend_cache()


def test_cache_key_normalises_equivalent_paths(project, monkeypatch):
    """AA-OPT-026: dotted-equivalent paths resolve to one cache entry."""
    from asecli.bridge import backend as backend_module

    monkeypatch.setattr(backend_module, "probe_mcp", lambda *a, **k: {"ok": True, "reason": None})
    monkeypatch.setattr(backend_module, "bridge_probe", lambda r, **k: {"ok": False, "reason": "no"})
    monkeypatch.setattr(backend_module, "codely_probe", lambda r, **k: {"ok": False, "reason": "no"})
    backend_module.clear_backend_cache()
    try:
        backend_module.select_backend("auto", project / "Assets")
        backend_module.select_backend("auto", project / "Assets" / ".")
        assert len(backend_module._choice_cache) == 1
    finally:
        backend_module.clear_backend_cache()


def test_error_message_drops_stack_frames(project):
    """AA-OPT-024: multi-line probe errors surface as a single headline."""
    write_instance(project)

    def noisy(request):
        return _envelope(request, ok=False, error={
            "code": "runtime_error",
            "message": "boom first line\n  at Foo.Bar () [0x00000]\n  at Baz.Qux ()"})

    editor = FakeEditor(project, noisy)
    editor.start()
    try:
        with BridgeClient(project, timeout=5) as client:
            with pytest.raises(BridgeError) as excinfo:
                client.execute_code("return 1;")
    finally:
        editor.stop()
    assert "\n" not in str(excinfo.value)
    assert "at Foo.Bar" not in str(excinfo.value)
    assert "at Foo.Bar" in excinfo.value.data["detail"]


def test_probe_reports_capability_level(project):
    """AA-OPT-034: callers must be able to see this transport's privileges."""
    write_instance(project)
    editor = FakeEditor(project, ok_answer("asecli-probe-ok"))
    editor.start()
    try:
        result = probe(project, timeout=5)
    finally:
        editor.stop()
    assert result["ok"] is True
    assert result["capability_level"] == "unrestricted-code"


def test_no_mcp_only_wording_outside_the_mcp_client():
    """AA-OPT-033: transport-level errors must not claim to be MCP-specific."""
    import asecli.bridge as bridge_pkg

    root = Path(bridge_pkg.__file__).parent
    offenders = []
    for path in root.glob("*.py"):
        if path.name == "mcp_client.py":
            continue  # genuinely MCP-only
        text = path.read_text(encoding="utf-8")
        if '"MCP ' in text or 'f"MCP ' in text:
            offenders.append(path.name)
    assert offenders == []


def test_late_answer_within_grace_is_adopted(project):
    """AA-OPT-035: work already triggered must not be reported as a failure."""
    write_instance(project)

    def slow_ok(request):
        time.sleep(0.12)
        return _envelope(request, data={"result": "LATE-SUCCESS", "resultTruncated": False})

    editor = FakeEditor(project, slow_ok)
    editor.start()
    try:
        with BridgeClient(project, timeout=0.1) as client:
            assert client.execute_code("return 1;") == "LATE-SUCCESS"
    finally:
        editor.stop()


def test_unknown_backend_is_rejected_by_payload_extraction():
    """AA-OPT-037: an unknown backend name must not silently pick a branch."""
    from asecli.bridge.editor_result import extract_payload

    with pytest.raises(ValueError, match="unknown backend"):
        extract_payload("anything", "typo")
    assert extract_payload("bare", "raw") == "bare"


def test_timeout_after_processing_is_reported_as_processed(project):
    """AA-OPT-040: a done/ marker proves work was taken up even without an answer."""
    write_instance(project)
    done = project / "Library" / "DSHBridge" / "boot01" / "done"

    def take_and_vanish(request):
        # Mimic the probe: move the request into done/, then fail to answer.
        (done / f"{request['id']}.json").write_text(json.dumps(request))
        return None

    editor = FakeEditor(project, take_and_vanish)
    editor.start()
    try:
        with BridgeClient(project, timeout=0.5) as client:
            with pytest.raises(BridgeError) as excinfo:
                client.execute_code("return 1;")
    finally:
        editor.stop()
    error = excinfo.value
    assert error.data["execution_state"] == "processed"
    assert error.data["processed"] is True
    assert "may already have run" in str(error) or "already been handled" in str(error)


def test_payload_limit_is_per_transport():
    """AA-LOGIC-043: only mcp-for-unity enforces the 50000-character ceiling."""
    import random
    import string

    from asecli.bridge.editor_create import MCP_CODE_LIMIT, build_executor_code

    random.seed(7)
    incompressible = {"blob": "".join(random.choices(string.ascii_letters, k=120_000))}

    with pytest.raises(ValueError, match="over the"):
        build_executor_code(incompressible)
    assert MCP_CODE_LIMIT == 50000

    # Other transports must not inherit mcp's ceiling.
    code = build_executor_code(incompressible, limit=None)
    assert len(code) > MCP_CODE_LIMIT
