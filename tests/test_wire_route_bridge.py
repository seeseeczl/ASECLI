"""WireNode routing uses a fixed, capability-probed Editor transaction."""

from __future__ import annotations

import base64
import json

import pytest

from asecli.bridge.mcp_client import McpError
from asecli.bridge.wire_route import WIRE_ROUTE_SNIPPET, apply_wire_routes_via_mcp


def _target(tmp_path):
    root = tmp_path / "Project"
    (root / "Assets").mkdir(parents=True)
    (root / "ProjectSettings").mkdir()
    target = root / "Assets" / "Route.shader"
    target.write_text('Shader "Test" {}\n', encoding="utf-8")
    return target


def _change():
    return ({
        "action": "add",
        "logical_wire": {"from_node": "1", "from_port": "0", "to_node": "2", "to_port": "3"},
        "anchors": [[120.0, 40.0], [220.0, 40.0]],
    },)


def test_wire_route_executor_probes_api_saves_rolls_back_and_restores_editor_state():
    for token in (
        'GetMethod(\n        "CreateNode"',
        'GetMethod(\n        "CreateConnection"',
        'GetMethod(\n        "DeleteConnection"',
        "typeof(AmplifyShaderEditor.WireNode)",
        "graphDeleteConnection.Invoke",
        "saveMethod.Invoke",
        "File.WriteAllBytes",
        "AssetDatabase.ImportAsset",
        "AmplifyShaderEditor.UIUtils.CurrentWindow = previousWindow",
        "win.Close()",
        "DestroyImmediate(win)",
    ):
        assert token in WIRE_ROUTE_SNIPPET
    assert WIRE_ROUTE_SNIPPET.count("{payload_base64}") == 1
    assert 'aseVersion != "1.9.6.2"' not in WIRE_ROUTE_SNIPPET


def test_wire_route_payload_is_base64_data_and_result_is_strict(tmp_path, monkeypatch):
    target = _target(tmp_path)
    seen = {}

    class Client:
        def __init__(self, *args, **kwargs):
            pass

        def connect(self):
            return {}

        def call_tool(self, name, arguments):
            seen.update(arguments)
            encoded = arguments["code"].split('FromBase64String("', 1)[1].split('")', 1)[0]
            payload = json.loads(base64.b64decode(encoded))
            assert payload == {
                "asset_path": "Assets/Route.shader",
                "routes": [{
                    "action": "add",
                    "anchors": [[120.0, 40.0], [220.0, 40.0]],
                    "logical_wire": {"from_node": 1, "from_port": 0, "to_node": 2, "to_port": 3},
                }],
                "version": 1,
            }
            result = {
                "protocol": "ASECLI_WIRE_ROUTE_V1", "asset_path": payload["asset_path"],
                "ase_version": "1.9.8.1", "saved": True, "applied_routes": 1,
                "created_node_ids": [40, 41],
            }
            envelope = {"success": True, "data": {"result": "ASECLI_WIRE_ROUTE_V1:" + json.dumps(result)}}
            return {"content": [{"type": "text", "text": json.dumps(envelope)}]}

    monkeypatch.setattr("asecli.bridge.wire_route.McpClient", Client)
    result = apply_wire_routes_via_mcp(target, _change(), unity_instance="Project@123")
    assert result["created_node_ids"] == [40, 41]
    assert seen["unity_instance"] == "Project@123"


def test_wire_route_rejects_more_than_two_new_anchors_before_mcp(tmp_path):
    target = _target(tmp_path)
    change = _change()[0] | {"anchors": [[1, 1], [2, 2], [3, 3]]}
    with pytest.raises(ValueError, match="one or two"):
        apply_wire_routes_via_mcp(target, (change,))


def test_wire_route_rejects_unconfirmed_editor_result(tmp_path, monkeypatch):
    target = _target(tmp_path)

    class Client:
        def __init__(self, *args, **kwargs):
            pass

        def connect(self):
            return {}

        def call_tool(self, name, arguments):
            result = {
                "protocol": "ASECLI_WIRE_ROUTE_V1", "asset_path": "Assets/Route.shader",
                "saved": False, "applied_routes": 1, "created_node_ids": [40, 41],
            }
            return {"content": [{"type": "text", "text": "ASECLI_WIRE_ROUTE_V1:" + json.dumps(result)}]}

    monkeypatch.setattr("asecli.bridge.wire_route.McpClient", Client)
    with pytest.raises(McpError, match="saved=True"):
        apply_wire_routes_via_mcp(target, _change())
