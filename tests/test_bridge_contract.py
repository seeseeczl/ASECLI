"""REG-0016: MCP transport and tool failures must not become false success."""

import json
from types import SimpleNamespace

import pytest

from asecli.bridge.mcp_client import McpClient, McpError
from asecli.bridge.recompile import RECOMPILE_SNIPPET, recompile_via_mcp
from asecli.bridge.graph_inspect import BOUNDS_SNIPPET, measure_node_bounds_via_mcp
from asecli.bridge.graph_geometry import GEOMETRY_SNIPPET, inspect_graph_geometry_via_mcp
from asecli.core import AseFile, meticulous_layout_positions


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


def test_geometry_probe_requires_true_position_header_and_port_anchors():
    assert "node.TruePosition" in GEOMETRY_SNIPPET
    assert "node.GlobalPosition" in GEOMETRY_SNIPPET
    assert "global.width / rect.width" in GEOMETRY_SNIPPET
    assert "(screenCenter.x - global.x) / scaleX" in GEOMETRY_SNIPPET
    assert "if (rect.width <= 0 || rect.height <= 0) continue" in GEOMETRY_SNIPPET
    assert 'findMember(nodeType, "HeaderPosition")' in GEOMETRY_SNIPPET
    assert "type = type.BaseType" in GEOMETRY_SNIPPET
    assert "node.InputPorts" in GEOMETRY_SNIPPET
    assert "node.OutputPorts" in GEOMETRY_SNIPPET
    assert "ASECLI_GEOMETRY_V3" in GEOMETRY_SNIPPET
    assert "probeNode.OnNodeLogicUpdate(probeDraw)" in GEOMETRY_SNIPPET
    assert "probeNode.OnNodeLayout(probeDraw)" in GEOMETRY_SNIPPET
    assert "probeDraw.CameraArea" in GEOMETRY_SNIPPET
    assert "input_port_labels" not in GEOMETRY_SNIPPET  # labels are transported, not hard-coded
    assert "AmplifyShaderEditor.UIUtils.CurrentWindow = previousWindow" in GEOMETRY_SNIPPET
    assert "DestroyImmediate(win)" in GEOMETRY_SNIPPET


def test_bounds_probe_routes_to_explicit_unity_instance(tmp_path, monkeypatch):
    shader = _shader_project(tmp_path)
    seen = {}

    class SuccessClient:
        def __init__(self, *args, **kwargs):
            pass

        def connect(self):
            return {}

        def call_tool(self, name, arguments):
            seen.update(arguments)
            envelope = {"success": True, "data": {"result": "ASECLI_BOUNDS_V1\n1|0|0|100|50\n"}}
            return {"content": [{"type": "text", "text": json.dumps(envelope)}]}

    monkeypatch.setattr("asecli.bridge.graph_inspect.McpClient", SuccessClient)
    bounds = measure_node_bounds_via_mcp(str(shader), unity_instance="Project@abc123")
    assert seen["unity_instance"] == "Project@abc123"
    assert bounds == {"1": (0.0, 0.0, 100.0, 50.0)}


def test_bounds_probe_surfaces_multiple_instance_refusal(tmp_path, monkeypatch):
    shader = _shader_project(tmp_path)

    class RefusingClient:
        def __init__(self, *args, **kwargs):
            pass

        def connect(self):
            return {}

        def call_tool(self, name, arguments):
            envelope = {
                "success": False,
                "data": {
                    "reason": "instance_selection_required",
                    "available_instances": ["A@111", "B@222"],
                },
            }
            return {"content": [{"type": "text", "text": json.dumps(envelope)}]}

    monkeypatch.setattr("asecli.bridge.graph_inspect.McpClient", RefusingClient)
    with pytest.raises(McpError, match="available instances: A@111, B@222"):
        measure_node_bounds_via_mcp(str(shader))


def test_geometry_probe_returns_relative_port_offsets(tmp_path, monkeypatch):
    shader = _shader_project(tmp_path)

    class SuccessClient:
        def __init__(self, *args, **kwargs):
            pass

        def connect(self):
            return {}

        def call_tool(self, name, arguments):
            payload = "ASECLI_GEOMETRY_V2\nN|1|100|200|180|90|24\nI|1|0|100|230\nO|1|2|280|240\n"
            return {"content": [{"type": "text", "text": json.dumps({"success": True, "data": {"result": payload}})}]}

    monkeypatch.setattr("asecli.bridge.graph_geometry.McpClient", SuccessClient)
    geometry = inspect_graph_geometry_via_mcp(str(shader))["1"]
    assert (geometry.width, geometry.height, geometry.title_height) == (180.0, 90.0, 24.0)
    assert geometry.input_ports == {"0": (0.0, 30.0)}
    assert geometry.output_ports == {"2": (180.0, 40.0)}


def test_geometry_v3_probe_decodes_optional_node_and_port_labels(tmp_path, monkeypatch):
    shader = _shader_project(tmp_path)

    class SuccessClient:
        def __init__(self, *args, **kwargs):
            pass

        def connect(self):
            return {}

        def call_tool(self, name, arguments):
            payload = "ASECLI_GEOMETRY_V3\nN|1|100|200|180|90|24|Q3VzdG9tIEZ1bmN0aW9u\nI|1|0|100|230|U3RyZW5ndGg=\nO|1|2|280|240|T3V0\n"
            return {"content": [{"type": "text", "text": json.dumps({"success": True, "data": {"result": payload}})}]}

    monkeypatch.setattr("asecli.bridge.graph_geometry.McpClient", SuccessClient)
    geometry = inspect_graph_geometry_via_mcp(str(shader))["1"]
    assert geometry.node_title == "Custom Function"
    assert geometry.input_port_labels == {"0": "Strength"}
    assert geometry.output_port_labels == {"2": "Out"}


def test_layout_ignores_unrendered_disconnected_multipass_master_placeholder():
    shader = AseFile.from_text("""/*ASEBEGIN
Version=19602
Node;AmplifyShaderEditor.TemplateMultiPassMasterNode;0;0,0
Node;AmplifyShaderEditor.RangedFloatNode;1;0,0
Node;AmplifyShaderEditor.TemplateMultiPassMasterNode;100;0,0
WireConnection;100;0;1;0
ASEEND*/""")
    geometry = {
        "1": SimpleNamespace(width=180, height=100, title_height=24, input_ports={}, output_ports={"0": (180, 40)}),
        "100": SimpleNamespace(width=180, height=100, title_height=24, input_ports={"0": (0, 40)}, output_ports={}),
    }
    assert set(meticulous_layout_positions(shader.graph, geometry).positions) == {"1", "100"}


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
