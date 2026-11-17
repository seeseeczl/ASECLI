"""Every editor-facing CLI switch must actually reach the transport.

A switch that parses but is never forwarded looks identical to a working one
from the user's side, so these tests assert the *downstream* call received the
requested backend rather than just that the command succeeded.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from asecli.cli.main import app
from asecli.cli import commentary_command, create_command, gui_support_command

@pytest.fixture
def shader(tmp_path):
    """A structurally valid ASE file, so commands get past parsing."""
    from asecli.checks import fix_checksum
    from asecli.core import ASECLI_GUI_EDITOR

    root = tmp_path / "Project"
    (root / "Assets").mkdir(parents=True)
    (root / "ProjectSettings").mkdir()
    text = (
        'Shader "Tests/Forward"\n{\n\tSubShader {}\n'
        f'\tCustomEditor "{ASECLI_GUI_EDITOR}"\n\tFallback Off\n}}\n'
        "/*ASEBEGIN\nVersion=19602\n"
        "Node;AmplifyShaderEditor.TemplateMultiPassMasterNode;0;0,0;Float;False;False;-1;2;"
        f"{ASECLI_GUI_EDITOR};0;1;Secondary;0\n"
        "ASEEND*/\n//CHKSM=PLACEHOLDER"
    )
    path = root / "Assets" / "T.shader"
    path.write_text(fix_checksum(text), encoding="utf-8")
    return path


def _capture(monkeypatch, module, name, returns):
    """Replace ``module.name`` with a spy recording its kwargs."""
    seen: list[dict] = []

    def spy(*args, **kwargs):
        seen.append(kwargs)
        return returns

    monkeypatch.setattr(module, name, spy)
    return seen


def test_comment_group_forwards_backend(shader, monkeypatch, capsys):
    seen = _capture(monkeypatch, commentary_command, "measure_node_bounds_via_mcp", {})
    app(["comment-group", str(shader), "--editor-backend", "codely", "--check-bounds"])
    capsys.readouterr()
    assert seen, "measure_node_bounds_via_mcp was never called"
    assert seen[0]["backend"] == "codely"


def test_create_forwards_backend(shader, monkeypatch, capsys, tmp_path):
    seen = _capture(monkeypatch, create_command, "create_shader_via_mcp",
                    {"transport": "codely", "saved": True})
    monkeypatch.setattr(create_command, "select_editor_provider", lambda out: ("fallback", None))
    from tests.editor_create_v3_fixture import algorithm_spec

    target = tmp_path / "Project" / "Assets" / "New.shader"
    spec = tmp_path / "spec.json"
    spec.write_text(json.dumps(algorithm_spec("2992e84f91cbeb14eab234972e07ea9d")), encoding="utf-8")
    app(["create", str(target), "--backend", "editor", "--spec", str(spec),
         "--editor-backend", "bridge"])
    capsys.readouterr()
    assert seen, "create_shader_via_mcp was never called"
    assert seen[0]["backend"] == "bridge"


def test_gui_support_forwards_backend(shader, monkeypatch, capsys):
    seen = _capture(monkeypatch, gui_support_command, "probe_native_mzgui_via_mcp", None)
    monkeypatch.setattr(gui_support_command, "install_gui_support",
                        lambda *a, **k: {"provider": "native_mzgui"})
    app(["gui-support", str(shader.parents[1]), "--runtime-probe", "--editor-backend", "codely"])
    capsys.readouterr()
    assert seen, "probe_native_mzgui_via_mcp was never called"
    assert seen[0]["backend"] == "codely"


def test_gui_probe_no_longer_hardcodes_mcp():
    """AA-LOGIC-031: the runtime probe must go through the shared entry point."""
    from asecli.bridge import gui_provider_detection as module

    source = Path(module.__file__).read_text(encoding="utf-8")
    body = source[source.index("def probe_native_mzgui_for_assets"):]
    body = body[:body.index("\ndef ")] if "\ndef " in body else body
    assert "run_editor_code" in body
    assert "McpClient(" not in body


def test_layout_forwards_backend(shader, monkeypatch, capsys):
    """Layout's geometry inspection must honour the requested backend."""
    from asecli.cli import layout_command

    seen = _capture(monkeypatch, layout_command, "inspect_graph_geometry_via_mcp", {})
    app(["layout", str(shader), "--mode", "meticulous", "--editor-backend", "codely"])
    capsys.readouterr()
    assert seen, "inspect_graph_geometry_via_mcp was never called"
    assert seen[0]["backend"] == "codely"
