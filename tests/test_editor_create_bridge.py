"""REG-0027: fixed Editor executor, capability gates and honest MCP results."""

from __future__ import annotations

import base64
import hashlib
import json
from pathlib import Path

import pytest

from asecli.bridge.editor_create import (
    EDITOR_CREATE_RESOURCE_PARTS,
    EDITOR_CREATE_SNIPPET,
    create_shader_via_mcp,
)
from asecli.bridge.editor_spec import EditorGraphSpec
from asecli.bridge.mcp_client import McpError


TEMPLATE_GUID = "2992e84f91cbeb14eab234972e07ea9d"
ROOT = Path(__file__).parents[1]


def caster_spec() -> dict:
    return {
        "version": 1,
        "template": {"guid": TEMPLATE_GUID, "shader_name": "Tests/EditorCaster"},
        "nodes": [
            {
                "alias": "mask",
                "kind": "sampler",
                "position": [-520, 20],
                "property_name": "_CasterMask",
                "inspector_name": "Caster Mask",
                "parameter_type": "Property",
            }
        ],
        "connections": [
            {"from": {"node": "mask", "port": 1}, "to": {"node": "master", "port": 2}}
        ],
    }


def _project_target(tmp_path):
    root = tmp_path / "Project"
    (root / "Assets" / "Generated").mkdir(parents=True)
    (root / "ProjectSettings").mkdir()
    return root / "Assets" / "Generated" / "Caster.shader"


def _success_result(asset_path: str, manifest: dict) -> str:
    payload = {
        "protocol": "ASECLI_EDITOR_CREATE_V1",
        "ase_version": "1.9.6.2",
        "asset_path": asset_path,
        "template_guid": manifest["template"]["guid"],
        "shader_name": manifest["template"]["shader_name"],
        "saved": True,
        "reloaded": True,
        "committed": True,
        "manifest": manifest,
    }
    return "ASECLI_EDITOR_CREATE_V1:" + json.dumps(payload, separators=(",", ":"))


def _execute_code_envelope(result: str) -> str:
    return json.dumps(
        {
            "success": True,
            "message": "Code executed successfully.",
            "data": {"result": result, "compiler": "codedom"},
        },
        separators=(",", ":"),
    )


def test_executor_is_fixed_version_gated_transactional_and_closes_windows():
    required = [
        "VersionInfo.StaticToString()",
        '"1.9.6.2"',
        'GetField("m_customExpressionName"',
        'GetField("m_items"',
        'GetField("m_code"',
        'GetField("m_outputTypeIdx"',
        'GetField("m_functionMode"',
        '"m_currentPrecisionType"',
        '"m_min"',
        '"m_max"',
        "CreateNewTemplateShader",
        "CreateNode",
        "CreateConnection",
        "sampler.AutoRegister = true",
        "property.AutoRegister = true",
        "SaveToDisk(false)",
        "LoadFromDisk",
        "AssetDatabase.MoveAsset",
        "AssetDatabase.DeleteAsset",
        "UnityEditor.Selection.activeObject = previousSelection",
        "AmplifyShaderEditor.UIUtils.CurrentWindow = previousWindow",
        "win.Close()",
        "DestroyImmediate(win)",
    ]
    for token in required:
        assert token in EDITOR_CREATE_SNIPPET
    assert EDITOR_CREATE_SNIPPET.index('"1.9.6.2"') < EDITOR_CREATE_SNIPPET.index("CreateNewTemplateShader")
    assert 'templateGuid, temporaryAssetPath, shaderName + ".shader"' in EDITOR_CREATE_SNIPPET
    assert EDITOR_CREATE_SNIPPET.index("createdWindow.Close()") < EDITOR_CREATE_SNIPPET.index("success = true")
    assert EDITOR_CREATE_SNIPPET.index("stateRestored = true") < EDITOR_CREATE_SNIPPET.index("success = true")
    assert 'failure.Data["ASECLI cleanup failures"]' in EDITOR_CREATE_SNIPPET
    assert "precisionField.GetValue(actualNode)).ToString()" in EDITOR_CREATE_SNIPPET
    post_commit = EDITOR_CREATE_SNIPPET.split("AssetDatabase.MoveAsset", 1)[1].split("catch (System.Exception ex)", 1)[0]
    assert "AssetDatabase.Refresh" not in post_commit
    assert "LoadFromDisk(assetPath" not in post_commit


def test_editor_executor_fragments_preserve_one_byte_stable_transaction_payload():
    resources = ROOT / "src/asecli/bridge/resources"
    parts = [resources / name for name in EDITOR_CREATE_RESOURCE_PARTS]
    assert all(path.is_file() for path in parts)
    assert all(len(path.read_text(encoding="utf-8").splitlines()) <= 400 for path in parts)
    assert "".join(path.read_text(encoding="utf-8") for path in parts) == EDITOR_CREATE_SNIPPET
    assert hashlib.sha256(EDITOR_CREATE_SNIPPET.encode("utf-8")).hexdigest() == (
        "dd1467b22b506d8fbcca2f6d5387521a7b32e7bf61d5ea5ec8a5c43b4d03c7f6"
    )
    assert EDITOR_CREATE_SNIPPET.count("{payload_base64}") == 1
    assert "public struct InputTarget" not in EDITOR_CREATE_SNIPPET
    assert "System.Tuple" not in EDITOR_CREATE_SNIPPET
    assert "float[] values = " in EDITOR_CREATE_SNIPPET
    assert EDITOR_CREATE_SNIPPET.count("catch (System.Exception ex)") == 1
    assert EDITOR_CREATE_SNIPPET.count("finally\n{") == 1


def test_payload_is_base64_json_not_csharp_interpolation(tmp_path, monkeypatch):
    target = _project_target(tmp_path)
    spec = EditorGraphSpec.from_dict(caster_spec())
    seen = {}

    class Client:
        def __init__(self, *args, **kwargs):
            pass

        def connect(self):
            return {}

        def call_tool(self, name, arguments):
            seen.update(arguments)
            code = arguments["code"]
            encoded = code.split('FromBase64String("', 1)[1].split('")', 1)[0]
            decoded = json.loads(base64.b64decode(encoded).decode("utf-8"))
            assert decoded["template"]["shader_name"] == "Tests/EditorCaster"
            assert decoded["temporary_asset_path"].split("/")[-1].startswith("ASECLI-Temp-")
            assert "Tests/EditorCaster" not in code
            target.write_text('Shader "Tests/EditorCaster" {}\n/*ASEBEGIN\nVersion=19602\nASEEND*/\n//CHKSM=0\n')
            return {"content": [{"type": "text", "text": _success_result(decoded["asset_path"], spec.expected_manifest())}]}

    monkeypatch.setattr("asecli.bridge.editor_create.McpClient", Client)
    result = create_shader_via_mcp(target, spec)

    assert seen["action"] == "execute"
    assert seen["safety_checks"] is False
    assert result["saved"] is True
    assert result["reloaded"] is True
    assert result["staging_reloaded"] is True
    assert result["target_graph_reloaded"] is False
    assert result["changed"] is True
    assert len(result["transaction_nonce"]) == 32
    assert result["transaction_nonce"] in json.loads(
        base64.b64decode(seen["code"].split('FromBase64String("', 1)[1].split('")', 1)[0]).decode("utf-8")
    )["temporary_asset_path"]
    assert result["shader_sha256"] == hashlib.sha256(target.read_bytes()).hexdigest()
    assert result["meta_sha256"] is None


def test_current_execute_code_json_envelope_is_unwrapped(tmp_path, monkeypatch):
    target = _project_target(tmp_path)
    spec = EditorGraphSpec.from_dict(caster_spec())

    class Client:
        def __init__(self, *args, **kwargs):
            pass

        def connect(self):
            return {}

        def call_tool(self, name, arguments):
            encoded = arguments["code"].split('FromBase64String("', 1)[1].split('")', 1)[0]
            decoded = json.loads(base64.b64decode(encoded).decode("utf-8"))
            target.write_text('Shader "Tests/EditorCaster" {}\n/*ASEBEGIN\nVersion=19602\nASEEND*/\n//CHKSM=0\n')
            protocol_result = _success_result(decoded["asset_path"], spec.expected_manifest())
            return {"content": [{"type": "text", "text": _execute_code_envelope(protocol_result)}]}

    monkeypatch.setattr("asecli.bridge.editor_create.McpClient", Client)
    result = create_shader_via_mcp(target, spec)

    assert result["committed"] is True
    assert result["manifest"] == spec.expected_manifest()


def test_current_execute_code_failure_envelope_fails_closed(tmp_path, monkeypatch):
    target = _project_target(tmp_path)
    spec = EditorGraphSpec.from_dict(caster_spec())

    class Client:
        def __init__(self, *args, **kwargs):
            pass

        def connect(self):
            return {}

        def call_tool(self, name, arguments):
            return {
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps(
                            {"success": False, "message": "compiler blocked", "data": None}
                        ),
                    }
                ]
            }

    monkeypatch.setattr("asecli.bridge.editor_create.McpClient", Client)
    with pytest.raises(McpError, match="compiler blocked"):
        create_shader_via_mcp(target, spec)

    assert not target.exists()


@pytest.mark.parametrize(
    "payload_update, match",
    [
        ({"saved": False}, "saved"),
        ({"reloaded": False}, "reloaded"),
        ({"committed": False}, "committed"),
        ({"ase_version": "1.9.81"}, "version"),
        ({"template_guid": "0" * 32}, "template guid"),
        ({"shader_name": "Wrong/Shader"}, "shader name"),
    ],
)
def test_unconfirmed_editor_result_fails_closed(tmp_path, monkeypatch, payload_update, match):
    target = _project_target(tmp_path)
    spec = EditorGraphSpec.from_dict(caster_spec())

    class Client:
        def __init__(self, *args, **kwargs):
            pass

        def connect(self):
            return {}

        def call_tool(self, name, arguments):
            data = json.loads(_success_result("Assets/Generated/Caster.shader", spec.expected_manifest()).split(":", 1)[1])
            data.update(payload_update)
            return {"content": [{"type": "text", "text": "ASECLI_EDITOR_CREATE_V1:" + json.dumps(data)}]}

    monkeypatch.setattr("asecli.bridge.editor_create.McpClient", Client)
    with pytest.raises(McpError, match=match):
        create_shader_via_mcp(target, spec)


def test_manifest_mismatch_and_outside_assets_path_fail_closed(tmp_path, monkeypatch):
    target = _project_target(tmp_path)
    spec = EditorGraphSpec.from_dict(caster_spec())

    class Client:
        def __init__(self, *args, **kwargs):
            pass

        def connect(self):
            return {}

        def call_tool(self, name, arguments):
            wrong_manifest = {**spec.expected_manifest(), "nodes": []}
            return {"content": [{"type": "text", "text": _success_result("Assets/Generated/Caster.shader", wrong_manifest)}]}

    monkeypatch.setattr("asecli.bridge.editor_create.McpClient", Client)
    with pytest.raises(McpError, match="manifest"):
        create_shader_via_mcp(target, spec)

    outside = target.parents[2] / "outside.shader"
    with pytest.raises(ValueError, match="Assets"):
        create_shader_via_mcp(outside, spec)
