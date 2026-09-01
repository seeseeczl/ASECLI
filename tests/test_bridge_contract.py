"""REG-0016: MCP transport and tool failures must not become false success."""

import json

import pytest

from asecli.bridge.mcp_client import McpClient, McpError
from asecli.bridge.recompile import RECOMPILE_SNIPPET, recompile_via_mcp
from asecli.bridge.graph_inspect import BOUNDS_SNIPPET


def _shader_project(tmp_path):
    root = tmp_path / "Project"
    (root / "Assets").mkdir(parents=True)
    (root / "ProjectSettings").mkdir()
    shader = root / "Assets" / "test.shader"
    shader.write_text('Shader "Test" {}\n', encoding="utf-8")
    return shader


def test_recompile_restores_ase_text_info_before_save():
    assert 'GetField(\n        "m_textInfo"' in RECOMPILE_SNIPPET
    assert "uiTextInfo.GetValue(null) == null" in RECOMPILE_SNIPPET
    assert RECOMPILE_SNIPPET.index("uiTextInfo.SetValue") < RECOMPILE_SNIPPET.index("win.SaveToDisk")


def test_recompile_loads_commentary_nodes_inside_real_gui_event():
    assert '"m_delayedLoadObject"' in RECOMPILE_SNIPPET
    assert "delayedLoad.SetValue(win, shader)" in RECOMPILE_SNIPPET
    assert "win.SendEvent(layoutEvent)" in RECOMPILE_SNIPPET
    assert "win.SendEvent(repaintEvent)" in RECOMPILE_SNIPPET
    assert RECOMPILE_SNIPPET.index("delayedLoad.SetValue") < RECOMPILE_SNIPPET.index("win.SendEvent(layoutEvent)")
    assert RECOMPILE_SNIPPET.index("win.SendEvent(repaintEvent)") < RECOMPILE_SNIPPET.index("win.SaveToDisk")
    assert "UnityEditor.Selection.activeObject = previousSelection" in RECOMPILE_SNIPPET
    assert "win.Close()" in RECOMPILE_SNIPPET


def test_bounds_probe_uses_true_position_inside_real_gui_event_and_closes_window():
    assert '"m_delayedLoadObject"' in BOUNDS_SNIPPET
    assert "win.SendEvent(layoutEvent)" in BOUNDS_SNIPPET
    assert "win.SendEvent(repaintEvent)" in BOUNDS_SNIPPET
    assert "node.TruePosition" in BOUNDS_SNIPPET
    assert "ASECLI_BOUNDS_V1" in BOUNDS_SNIPPET
    assert "AmplifyShaderEditor.UIUtils.CurrentWindow = previousWindow" in BOUNDS_SNIPPET
    assert "win.Close()" in BOUNDS_SNIPPET
    assert "DestroyImmediate(win)" in BOUNDS_SNIPPET


def test_json_rpc_error_is_bridge_failure(monkeypatch):
    client = McpClient("http://127.0.0.1:8080/mcp")
    monkeypatch.setattr(
        client,
        "_post",
        lambda payload: {"jsonrpc": "2.0", "id": payload["id"], "error": {"code": -32000, "message": "boom"}},
    )
    with pytest.raises(McpError, match="boom"):
        client.call_tool("execute_code", {})


def test_tool_is_error_maps_to_cli_bridge_error(tmp_path, monkeypatch, capsys):
    from asecli.cli.main import app

    shader = _shader_project(tmp_path)

    class ErrorClient:
        def __init__(self, *args, **kwargs):
            pass

        def connect(self):
            return {}

        def call_tool(self, name, arguments):
            return {"isError": True, "content": [{"type": "text", "text": "Unity execution failed"}]}

    monkeypatch.setattr("asecli.bridge.recompile.McpClient", ErrorClient)
    rc = app(["recompile", str(shader)])
    payload = json.loads(capsys.readouterr().out)
    assert rc == 3
    assert payload["ok"] is False
    assert payload["error"]["code"] == "BRIDGE_ERROR"


@pytest.mark.parametrize("mutate, expected_changed", [(False, False), (True, True)])
def test_saved_result_reports_real_file_change(tmp_path, monkeypatch, mutate, expected_changed):
    shader = _shader_project(tmp_path)

    class SuccessClient:
        def __init__(self, *args, **kwargs):
            pass

        def connect(self):
            return {}

        def call_tool(self, name, arguments):
            if mutate:
                shader.write_text('Shader "Test" { SubShader {} }\n', encoding="utf-8")
            return {"content": [{"type": "text", "text": "recompiled, saved=True"}]}

    monkeypatch.setattr("asecli.bridge.recompile.McpClient", SuccessClient)
    data = recompile_via_mcp(str(shader))
    assert data["saved"] is True
    assert data["changed"] is expected_changed


def test_unconfirmed_saved_result_is_bridge_failure(tmp_path, monkeypatch):
    shader = _shader_project(tmp_path)

    class UnknownClient:
        def __init__(self, *args, **kwargs):
            pass

        def connect(self):
            return {}

        def call_tool(self, name, arguments):
            return {"content": [{"type": "text", "text": "execution complete"}]}

    monkeypatch.setattr("asecli.bridge.recompile.McpClient", UnknownClient)
    with pytest.raises(McpError, match="saved"):
        recompile_via_mcp(str(shader))
