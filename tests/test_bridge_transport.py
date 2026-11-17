"""DSH-Bridge transport: mailbox framing, discovery and error mapping.

A fake mailbox stands in for the editor so these run without a live bridge,
while still exercising the real request/response file protocol.
"""

from __future__ import annotations

import json
import os
import threading
import time
from pathlib import Path

import pytest

from asecli.bridge.backend import BackendError, run_editor_code, select_backend
from asecli.bridge.bridge_client import BridgeClient, BridgeError, instance_is_stale, read_instance
from asecli.bridge.bridge_probe import probe
from tests._bridge_harness import (  # noqa: F401  (fixtures re-exported for pytest)
    NONCE, FakeEditor, _envelope, ok_answer, project, write_instance,
)

def test_read_instance_requires_matching_project(project):
    write_instance(project)
    assert read_instance(project)["instanceId"] == "unity:abc123"
    other = project.parent / "Other"
    (other / "Assets").mkdir(parents=True)
    (other / "ProjectSettings").mkdir()
    assert read_instance(other) is None


def test_read_instance_rejects_foreign_project_path(project):
    record = write_instance(project)
    record["projectPath"] = "/elsewhere/Project"
    (project / "Library" / "DSHBridge" / "instance.json").write_text(json.dumps(record))
    assert read_instance(project) is None


def test_instance_staleness_follows_declared_threshold(project):
    record = write_instance(project, stale_after=60000)
    assert instance_is_stale(record) is False
    # A heartbeat far older than the declared 60s threshold must read as stale.
    old = dict(record, lastSeenAt=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(time.time() - 600)))
    assert instance_is_stale(old) is True


def test_client_round_trips_through_the_mailbox(project):
    write_instance(project)
    editor = FakeEditor(project, ok_answer('"payload-ok"'))
    editor.start()
    try:
        with BridgeClient(project, timeout=5) as client:
            assert client.execute_code("return 1;") == '"payload-ok"'
    finally:
        editor.stop()

    request = editor.requests[0]
    assert request["cap"] == "unity.code.execute"
    assert request["instanceId"] == "unity:abc123"
    assert request["nonce"] == NONCE
    assert request["args"] == {"code": "return 1;"}


def test_client_surfaces_a_bridge_error(project):
    write_instance(project)
    editor = FakeEditor(project, lambda r: _envelope(
        r, ok=False, error={"code": "compile_error", "message": "boom"}))
    editor.start()
    try:
        with BridgeClient(project, timeout=5) as client:
            with pytest.raises(BridgeError, match="boom"):
                client.execute_code("bad")
    finally:
        editor.stop()


def test_client_refuses_a_truncated_result(project):
    write_instance(project)
    editor = FakeEditor(project, lambda r: _envelope(
        r, data={"result": "x", "resultTruncated": True}))
    editor.start()
    try:
        with BridgeClient(project, timeout=5) as client:
            with pytest.raises(BridgeError, match="truncated"):
                client.execute_code("big")
    finally:
        editor.stop()


def test_client_times_out_without_an_answer(project):
    write_instance(project)
    editor = FakeEditor(project, lambda r: None)
    editor.start()
    try:
        with BridgeClient(project, timeout=0.3) as client:
            with pytest.raises(BridgeError, match="timed out"):
                client.execute_code("never")
    finally:
        editor.stop()


def test_probe_reports_missing_instance(project):
    result = probe(project)
    assert result["ok"] is False
    assert "no DSH-Bridge instance" in result["reason"]


def test_probe_succeeds_against_a_live_mailbox(project):
    write_instance(project)
    editor = FakeEditor(project, ok_answer("asecli-probe-ok"))
    editor.start()
    try:
        assert probe(project, timeout=5)["ok"] is True
    finally:
        editor.stop()


def test_select_backend_accepts_bridge(project):
    assert select_backend("bridge", project)[0] == "bridge"


def test_auto_prefers_bridge_over_codely(project):
    write_instance(project)
    editor = FakeEditor(project, ok_answer("asecli-probe-ok"))
    editor.start()
    try:
        assert select_backend("auto", project)[0] == "bridge"
    finally:
        editor.stop()


def test_run_editor_code_rejects_unity_instance_for_bridge(project):
    write_instance(project)
    with pytest.raises(BackendError, match="unity_instance is not supported"):
        run_editor_code(project, "code", backend="bridge", unity_instance="A@1")


# --- regression coverage for docs/adversarial-audits/2026-11-17-164913 ---


def test_timeout_reports_delivery_and_backlog(project):
    """AA-OPT-011/014: a timeout must say it may have run, and why it stalled."""
    write_instance(project)
    inbox = project / "Library" / "DSHBridge" / "boot01" / "inbox"
    # A malformed entry queued ahead of us, like a crash leftover.
    (inbox / "aaa_stuck.json").write_text("{not json")

    with BridgeClient(project, timeout=0.2) as client:
        with pytest.raises(BridgeError) as excinfo:
            client.execute_code("return 1;")
    error = excinfo.value
    assert error.phase == "timeout"
    assert error.data["delivery"] == "delivered"
    assert error.data["inbox_backlog"] >= 1
    assert "may already have run" in str(error)
    assert error.data["request_id"]


def test_stale_temp_files_are_cleared_before_delivery(project):
    """AA-OPT-011: our own crash leftovers must not queue ahead of new work."""
    write_instance(project)
    inbox = project / "Library" / "DSHBridge" / "boot01" / "inbox"
    leftover = inbox / ".req_asecli_aaaaaaaaaaaaaaaa.tmp"
    leftover.write_text("partial")

    editor = FakeEditor(project, ok_answer("done"))
    editor.start()
    try:
        with BridgeClient(project, timeout=5) as client:
                        assert client.execute_code("return 1;") == "done"
    finally:
        editor.stop()
    assert not leftover.exists()


def test_documented_response_location_matches_implementation():
    """AA-OPT-013: the docstring must name outbox, not done."""
    import asecli.bridge.bridge_client as module

    doc = module.__doc__ or ""
    assert "``outbox/``" in doc
    assert "``done/``" in doc
    # The stale claim was that the *answer* lands in done/.
    assert "answer appears in ``done/``" not in doc


def test_auto_decision_is_cached_between_calls(project, monkeypatch):
    """AA-OPT-012: repeated auto calls must not re-probe every backend."""
    from asecli.bridge import backend as backend_module

    write_instance(project)
    editor = FakeEditor(project, ok_answer("asecli-probe-ok"))
    editor.start()
    calls: list[int] = []
    original = backend_module.bridge_probe

    def counting(root, **kwargs):
        calls.append(1)
        return original(root, **kwargs)

    monkeypatch.setattr(backend_module, "bridge_probe", counting)
    backend_module.clear_backend_cache()
    try:
        assert backend_module.select_backend("auto", project)[0] == "bridge"
        assert backend_module.select_backend("auto", project)[0] == "bridge"
    finally:
        editor.stop()
        backend_module.clear_backend_cache()
    assert len(calls) == 1


def test_auto_failure_is_cached_briefly(project, monkeypatch):
    """AA-OPT-012: an all-backends-down sweep must not be repeated instantly."""
    from asecli.bridge import backend as backend_module

    calls: list[int] = []

    def failing_probe(root, **kwargs):
        calls.append(1)
        return {"ok": False, "reason": "down"}

    monkeypatch.setattr(backend_module, "bridge_probe", failing_probe)
    monkeypatch.setattr(backend_module, "codely_probe", lambda root, **kw: {"ok": False, "reason": "down"})
    monkeypatch.setattr(backend_module, "probe_mcp", lambda *a, **kw: {"ok": False, "reason": "down"})
    backend_module.clear_backend_cache()
    try:
        for _ in range(3):
            with pytest.raises(BackendError):
                backend_module.select_backend("auto", project)
    finally:
        backend_module.clear_backend_cache()
    assert len(calls) == 1


# --- regression coverage for late responses (bridge probe 10 / requestHash round) ---


def test_late_response_after_timeout_is_accepted(project, monkeypatch):
    """A response that lands just after the deadline is still the right answer.

    The probe may finish a few milliseconds after we stop polling. Reporting
    "timeout, maybe it ran" while a valid result sits in ``outbox/`` is worse
    than the small extra read: it forces callers into a needless retry.
    """
    write_instance(project)
    timeout = 0.1
    started = time.monotonic()

    def read(request_id, outbox):
        # 轮询期间装作探针还没写完；过了 deadline 才给出合法响应。
        if time.monotonic() - started < timeout:
            return None
        return {
            "ok": True,
            "id": request_id,
            "instanceId": "unity:abc123",
            "bootId": "boot01",
            "nonce": NONCE,
            "executionState": "executed",
            "data": {"result": "late-done", "resultTruncated": False, "backend": "mono-mcs"},
        }

    monkeypatch.setattr(BridgeClient, "_read_response", staticmethod(read))
    with BridgeClient(project, timeout=timeout) as client:
        assert client.execute_code("return 1;") == "late-done"
        assert client.late_recovered == 1


def test_timeout_without_response_reports_not_processed(project):
    """An untouched request leaves no done/ marker, so a retry is safe."""
    write_instance(project)
    with BridgeClient(project, timeout=0.1) as client:
        with pytest.raises(BridgeError) as excinfo:
            client.execute_code("return 1;")
    error = excinfo.value
    assert error.phase == "timeout"
    # AA-OPT-040: absence of a done/ marker proves the probe never took it up.
    assert error.data["execution_state"] == "not-processed"
    assert error.data["processed"] is False
    # 旧的可用信息不能丢
    assert error.data["delivery"] == "delivered"
    assert error.data["request_id"]


def test_late_response_still_validates_ownership(project, monkeypatch):
    """A late file with foreign ownership is still refused, not accepted."""
    write_instance(project)
    timeout = 0.1
    started = time.monotonic()

    def read(request_id, outbox):
        if time.monotonic() - started < timeout:
            return None
        return {
            "ok": True,
            "id": request_id,
            "instanceId": "unity:abc123",
            "bootId": "boot01",
            "nonce": "not-our-nonce",
            "data": {"result": "planted", "resultTruncated": False},
        }

    monkeypatch.setattr(BridgeClient, "_read_response", staticmethod(read))
    with BridgeClient(project, timeout=timeout) as client:
        with pytest.raises(BridgeError) as excinfo:
            client.execute_code("return 1;")
    assert excinfo.value.phase == "protocol"


def test_live_suite_honours_the_project_override(tmp_path, monkeypatch):
    """AA-OPT-042: the documented ASECLI_TEST_PROJECT switch must really apply."""
    import subprocess
    import sys

    env = {
        **__import__("os").environ,
        "ASECLI_TEST_PROJECT": str(tmp_path / "elsewhere"),
        "PYTHONPATH": "src",
    }
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", "tests/test_bridge_live.py", "-q", "-p", "no:cacheprovider"],
        capture_output=True, text=True, env=env, cwd=str(Path(__file__).parents[1]),
    )
    # No instance record under the overridden path, so every case skips.
    assert "skipped" in proc.stdout
