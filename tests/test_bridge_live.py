"""Live-editor smoke tests for the DSH-Bridge transport.

These need a running editor with the bridge probe installed, so they carry the
``bridge`` marker and skip whenever no instance record is present:

    pytest -m bridge      # only these
    pytest                # everything else; these skip
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path

import pytest

from asecli.bridge.bridge_client import BRIDGE_ROOT, BridgeClient
from asecli.bridge.bridge_probe import CAPABILITY_LEVEL, probe

pytestmark = pytest.mark.bridge

#: Point ASECLI_TEST_PROJECT at another project to exercise a different editor.
PROJECT = Path(os.environ.get("ASECLI_TEST_PROJECT", "/Users/long/Tuanjie3D/P376"))


def _instance():
    record = PROJECT / BRIDGE_ROOT / "instance.json"
    if not record.is_file():
        pytest.skip(f"no live DSH-Bridge instance at {record}")
    try:
        data = json.loads(record.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        pytest.skip("bridge instance record is unreadable")
    if not data.get("instanceId"):
        pytest.skip("bridge instance record is incomplete")
    return data


def test_probe_reports_a_healthy_bridge():
    _instance()
    result = probe(PROJECT, timeout=60)
    if not result["ok"]:
        pytest.skip(f"bridge not ready: {result.get('reason')}")
    assert result["capability_level"] == CAPABILITY_LEVEL


def test_execute_code_round_trips():
    _instance()
    # A recompiling editor can drop a request; retry once before failing, since
    # the point is transport health rather than that transient state.
    last = None
    for _attempt in range(2):
        try:
            with BridgeClient(PROJECT, timeout=180) as client:
                assert client.execute_code("return 1+1;") == "2"
            return
        except Exception as exc:  # noqa: BLE001 - surfaced below if persistent
            last = exc
            time.sleep(1.0)
    raise AssertionError(f"bridge did not answer after 2 attempts: {last}")


def test_ase_private_field_is_reachable():
    """The snippets ASECLI ships depend on reading ASE's private state."""
    _instance()
    code = (
        "var asms = System.AppDomain.CurrentDomain.GetAssemblies();"
        'var node = asms.Select(a => a.GetType("AmplifyShaderEditor.PropertyNode"))'
        ".FirstOrDefault(t => t != null);"
        "if (node == null) return \"ase-missing\";"
        'var f = node.GetField("m_mzguiAttribs", System.Reflection.BindingFlags.Public'
        "| System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Instance);"
        'return f == null ? "field-missing" : f.Name;'
    )
    with BridgeClient(PROJECT, timeout=180) as client:
        result = client.execute_code(code)
    if result == "ase-missing":
        pytest.skip("Amplify Shader Editor is not loaded in this project")
    assert result == "m_mzguiAttribs"


def test_auto_backend_prefers_the_bridge():
    from asecli.bridge.backend import clear_backend_cache, select_backend

    _instance()
    last = None
    for _attempt in range(2):
        clear_backend_cache()
        try:
            backend, _details = select_backend("auto", PROJECT / "Assets")
        finally:
            clear_backend_cache()
        if backend == "bridge":
            return
        last = backend
        time.sleep(1.0)
    raise AssertionError(f"auto did not prefer bridge (got {last!r})")
