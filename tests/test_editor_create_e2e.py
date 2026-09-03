"""REG-0029: real ASE creation in an explicitly marked isolated Tuanjie project."""

from __future__ import annotations

import json
import os
from pathlib import Path
import re
import subprocess
import textwrap

import pytest

from asecli.bridge.editor_create import EDITOR_CREATE_SNIPPET
from asecli.bridge.editor_spec import EditorGraphSpec
from asecli.checks import validate_file
from asecli.cli.create_command import _finalize_editor_property_presentation
from asecli.core import AseFile, require_property_presentation


TEMPLATE_GUID = "2992e84f91cbeb14eab234972e07ea9d"
PROJECT_ENV = "ASECLI_EDITOR_CREATE_PROJECT"
EDITOR_ENV = "ASECLI_TUANJIE_PATH"


def _specs() -> tuple[EditorGraphSpec, EditorGraphSpec]:
    caster = {
        "version": 2,
        "template": {"guid": TEMPLATE_GUID, "shader_name": "ASECLI/E2E/Caster"},
        "nodes": [
            {"alias": "world", "kind": "node", "type": "WorldPosInputsNode", "position": [-420, -180]},
            {
                "alias": "mask", "kind": "sampler", "position": [-720, 20],
                "property_name": "_AuditMask", "inspector_name": "验证遮罩",
                "help": "用于验证动态纹理属性能够跨进程重新加载。", "parameter_type": "Property",
            },
            {
                "alias": "strength", "kind": "property", "type": "RangedFloatNode",
                "position": [-420, 20], "property_name": "_AuditStrength", "inspector_name": "验证强度",
                "help": "用于验证数值属性能够跨进程重新加载。", "parameter_type": "Property",
            },
        ],
        "connections": [
            {"from": {"node": "world", "port": 0}, "to": {"node": "master", "port": 2}},
            {"from": {"node": "strength", "port": 0}, "to": {"node": "master", "port": 3}},
        ],
    }
    receiver = {
        "version": 2,
        "template": {"guid": TEMPLATE_GUID, "shader_name": "ASECLI/E2E/Receiver"},
        "nodes": [
            {"alias": "world", "kind": "node", "type": "WorldPosInputsNode", "position": [-850, -80]},
            {
                "alias": "ground_mask", "kind": "property", "type": "TexturePropertyNode",
                "position": [-930, 300], "property_name": "_GroundMask", "inspector_name": "地面遮罩",
                "help": "控制局部阴影接收区域的遮罩纹理。", "parameter_type": "Property",
            },
            {"alias": "uv", "kind": "node", "type": "TextureCoordinatesNode", "position": [-930, 500]},
            {
                "alias": "expr", "kind": "custom_expression", "position": [-430, 10],
                "name": "Vehicle Local Shadow Core",
                "code": "return float3(WorldPosition.x, GroundMaskUV.y, 0);",
                "output_type": "FLOAT3",
                "inputs": [
                    {"name": "WorldPosition", "type": "FLOAT3"},
                    {"name": "GroundMaskUV", "type": "FLOAT2"},
                ],
            },
        ],
        "connections": [
            {"from": {"node": "world", "port": 0}, "to": {"node": "expr", "port": 0}},
            {"from": {"node": "uv", "port": 0}, "to": {"node": "expr", "port": 1}},
            {"from": {"node": "expr", "port": 0}, "to": {"node": "master", "port": 2}},
        ],
    }
    return EditorGraphSpec.from_dict(caster), EditorGraphSpec.from_dict(receiver)


@pytest.mark.bridge
def test_real_editor_create_then_new_process_reload():
    project_raw = os.environ.get(PROJECT_ENV)
    editor_raw = os.environ.get(EDITOR_ENV)
    if not project_raw or not editor_raw:
        pytest.skip(f"set {PROJECT_ENV} and {EDITOR_ENV} to run real Editor creation")
    project = Path(project_raw).resolve()
    editor = Path(editor_raw).resolve()
    if not (project / ".asecli-e2e-isolated").is_file():
        pytest.fail("refusing real Editor writes: isolated-project marker is missing")
    if not (project / "Assets" / "AmplifyShaderEditor").is_dir():
        pytest.fail("isolated project does not contain AmplifyShaderEditor")
    if not editor.is_file():
        pytest.fail(f"Tuanjie executable not found: {editor}")

    caster, receiver = _specs()
    generated = project / "Assets" / "ASECLIE2E" / "Generated"
    editor_dir = project / "Assets" / "ASECLIE2E" / "Editor"
    generated.mkdir(parents=True, exist_ok=True)
    # Tuanjie may remove a newly created empty Assets directory during its
    # first refresh before ASE writes the nonce-scoped staging shader.
    (generated / ".asecli-e2e-keep").write_text("keep\n", encoding="utf-8")
    editor_dir.mkdir(parents=True, exist_ok=True)
    caster_path = "Assets/ASECLIE2E/Generated/Caster.shader"
    receiver_path = "Assets/ASECLIE2E/Generated/Receiver.shader"
    close_failure_path = "Assets/ASECLIE2E/Generated/CloseFailure.shader"
    for relative in (caster_path, receiver_path, close_failure_path):
        target = project / relative
        assert not target.exists(), f"isolated E2E target already exists: {target}"

    caster_payload = caster.editor_payload(caster_path, "Assets/ASECLIE2E/Generated/ASECLI-Temp-e2e-caster.shader")
    receiver_payload = receiver.editor_payload(receiver_path, "Assets/ASECLIE2E/Generated/ASECLI-Temp-e2e-receiver.shader")
    close_failure_payload = caster.editor_payload(
        close_failure_path, "Assets/ASECLIE2E/Generated/ASECLI-Temp-e2e-close-failure.shader"
    )
    source = _harness_source(caster_payload, receiver_payload, close_failure_payload)
    harness = editor_dir / "ASECLIEditorCreateE2E.cs"
    harness.write_text(source, encoding="utf-8")

    create_log = project / "asecli-editor-create.log"
    _run_editor(editor, project, "ASECLIEditorCreateE2E.Run", create_log)
    result_path = project / "asecli-editor-create-result.json"
    result = json.loads(result_path.read_text(encoding="utf-8"))
    assert result["ok"] is True, result
    assert result["close_failure_rolled_back"] is True, result
    caster_result = json.loads(result["caster"].split("ASECLI_EDITOR_CREATE_V1:", 1)[1])
    receiver_result = json.loads(result["receiver"].split("ASECLI_EDITOR_CREATE_V1:", 1)[1])
    assert caster_result["manifest"] == caster.expected_manifest()
    assert receiver_result["manifest"] == receiver.expected_manifest()
    assert caster_result["template_guid"] == TEMPLATE_GUID
    assert receiver_result["template_guid"] == TEMPLATE_GUID
    assert caster_result["shader_name"] == "ASECLI/E2E/Caster"
    assert receiver_result["shader_name"] == "ASECLI/E2E/Receiver"

    for spec, relative in ((caster, caster_path), (receiver, receiver_path)):
        target = project / relative
        created = AseFile.from_path(target)
        output, presentation = _finalize_editor_property_presentation(created, spec)
        target.write_text(output, encoding="utf-8")
        assert presentation["valid"] is True

    reload_log = project / "asecli-editor-reload.log"
    _run_editor(editor, project, "ASECLIEditorCreateE2E.VerifyReload", reload_log)
    reload_result = json.loads((project / "asecli-editor-reload-result.json").read_text(encoding="utf-8"))
    assert reload_result == {"ok": True, "caster": True, "receiver": True}
    for log in (create_log, reload_log):
        text = log.read_text(encoding="utf-8", errors="replace")
        assert not any(marker in text for marker in ("Shader error", "failed to compile", "error CS", "Exception:"))
    assert not list(generated.glob("ASECLI-Temp-*"))
    assert not (project / close_failure_path).exists()
    assert not (project / f"{close_failure_path}.meta").exists()

    assert _shader_name(project / caster_path) == "ASECLI/E2E/Caster"
    assert _shader_name(project / receiver_path) == "ASECLI/E2E/Receiver"

    for relative in (caster_path, receiver_path):
        ase_file = AseFile.from_path(project / relative)
        errors = [issue for issue in validate_file(ase_file) if issue["severity"] == "error"]
        assert not errors
        assert ase_file.graph.nodes
        assert require_property_presentation(ase_file)["valid"] is True


def _shader_name(path: Path) -> str:
    match = re.search(r'^\s*Shader\s+"([^"\r\n]+)"', path.read_text(encoding="utf-8"), re.MULTILINE)
    assert match is not None, f"missing Shader declaration: {path}"
    return match.group(1)


def _run_editor(editor: Path, project: Path, method: str, log: Path) -> None:
    proc = subprocess.run(
        [str(editor), "-projectPath", str(project), "-executeMethod", method,
         "-logFile", str(log)],
        capture_output=True,
        text=True,
        timeout=600,
    )
    if proc.returncode != 0:
        tail = log.read_text(encoding="utf-8", errors="replace")[-12000:] if log.exists() else proc.stderr[-12000:]
        pytest.fail(f"Tuanjie {method} failed with {proc.returncode}:\n{tail}")


def _method_body(payload: dict, *, inject_close_failure: bool = False) -> str:
    import base64

    encoded = base64.b64encode(
        json.dumps(payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode("utf-8")
    ).decode("ascii")
    snippet = EDITOR_CREATE_SNIPPET.replace("{payload_base64}", encoded)
    if inject_close_failure:
        snippet = snippet.replace(
            "        createdWindow.Close();",
            '        throw new System.Exception("ASECLI_E2E_INJECTED_CLOSE_FAILURE");',
            1,
        )
    return textwrap.indent(snippet, "        ")


def _harness_source(caster_payload: dict, receiver_payload: dict, close_failure_payload: dict) -> str:
    return f'''using UnityEditor;
using UnityEngine;

public static class ASECLIEditorCreateE2E
{{
    public static void Run()
    {{
        var result = new Newtonsoft.Json.Linq.JObject();
        try
        {{
            result["caster"] = CreateCaster();
            result["receiver"] = CreateReceiver();
            result["close_failure_rolled_back"] = VerifyCloseFailureRollback();
            result["ok"] = true;
            System.IO.File.WriteAllText("asecli-editor-create-result.json", result.ToString(Newtonsoft.Json.Formatting.None));
            EditorApplication.Exit(0);
        }}
        catch (System.Exception ex)
        {{
            result["ok"] = false;
            result["error"] = ex.ToString();
            System.IO.File.WriteAllText("asecli-editor-create-result.json", result.ToString(Newtonsoft.Json.Formatting.None));
            Debug.LogException(ex);
            EditorApplication.Exit(1);
        }}
    }}

    private static string CreateCaster()
    {{
{_method_body(caster_payload)}
    }}

    private static string CreateReceiver()
    {{
{_method_body(receiver_payload)}
    }}

    private static string CreateCloseFailure()
    {{
{_method_body(close_failure_payload, inject_close_failure=True)}
    }}

    private static bool VerifyCloseFailureRollback()
    {{
        try
        {{
            CreateCloseFailure();
            return false;
        }}
        catch (System.Exception ex)
        {{
            AssetDatabase.Refresh();
            return ex.Message.Contains("ASECLI_E2E_INJECTED_CLOSE_FAILURE") &&
                AssetDatabase.LoadAssetAtPath<Object>(
                    "Assets/ASECLIE2E/Generated/CloseFailure.shader") == null &&
                !System.IO.File.Exists("Assets/ASECLIE2E/Generated/CloseFailure.shader") &&
                !System.IO.File.Exists("Assets/ASECLIE2E/Generated/CloseFailure.shader.meta") &&
                !System.IO.File.Exists(
                    "Assets/ASECLIE2E/Generated/ASECLI-Temp-e2e-close-failure.shader") &&
                !System.IO.File.Exists(
                    "Assets/ASECLIE2E/Generated/ASECLI-Temp-e2e-close-failure.shader.meta");
        }}
    }}

    public static void VerifyReload()
    {{
        var result = new Newtonsoft.Json.Linq.JObject();
        try
        {{
            result["caster"] = VerifyOne(
                "Assets/ASECLIE2E/Generated/Caster.shader", "ASECLI/E2E/Caster", true);
            result["receiver"] = VerifyOne(
                "Assets/ASECLIE2E/Generated/Receiver.shader", "ASECLI/E2E/Receiver", false);
            result["ok"] = true;
            System.IO.File.WriteAllText("asecli-editor-reload-result.json", result.ToString(Newtonsoft.Json.Formatting.None));
            EditorApplication.Exit(0);
        }}
        catch (System.Exception ex)
        {{
            result["ok"] = false;
            result["error"] = ex.ToString();
            System.IO.File.WriteAllText("asecli-editor-reload-result.json", result.ToString(Newtonsoft.Json.Formatting.None));
            Debug.LogException(ex);
            EditorApplication.Exit(1);
        }}
    }}

    private static bool VerifyOne(string path, string expectedShaderName, bool caster)
    {{
        var previous = AmplifyShaderEditor.UIUtils.CurrentWindow;
        AmplifyShaderEditor.AmplifyShaderEditorWindow win = null;
        try
        {{
            win = EditorWindow.CreateInstance<AmplifyShaderEditor.AmplifyShaderEditorWindow>();
            AmplifyShaderEditor.UIUtils.CurrentWindow = win;
            win.Show();
            AmplifyShaderEditor.ShaderLoadResult loaded;
            var previousInhibitMessages = AmplifyShaderEditor.UIUtils.InhibitMessages;
            try
            {{
                AmplifyShaderEditor.UIUtils.InhibitMessages = true;
                loaded = win.LoadFromDisk(path, null);
            }}
            finally
            {{
                AmplifyShaderEditor.UIUtils.InhibitMessages = previousInhibitMessages;
            }}
            if (loaded != AmplifyShaderEditor.ShaderLoadResult.LOADED &&
                loaded != AmplifyShaderEditor.ShaderLoadResult.TEMPLATE_LOADED) return false;
            var graph = win.CurrentGraph;
            var master = graph.CurrentMasterNode as AmplifyShaderEditor.TemplateMultiPassMasterNode;
            var shader = AssetDatabase.LoadAssetAtPath<Shader>(path);
            if (master == null || master.CurrentTemplate == null || shader == null ||
                master.CurrentTemplate.GUID != "{TEMPLATE_GUID}" ||
                master.ShaderName != expectedShaderName || shader.name != expectedShaderName) return false;
            if (caster)
            {{
                var sampler = graph.AllNodes.Find(n => n is AmplifyShaderEditor.SamplerNode) as AmplifyShaderEditor.SamplerNode;
                var strength = graph.AllNodes.Find(n => n is AmplifyShaderEditor.RangedFloatNode) as AmplifyShaderEditor.RangedFloatNode;
                var casterWorld = graph.AllNodes.Find(n => n is AmplifyShaderEditor.WorldPosInputsNode);
                return master.CurrentInspector == "ASECLI.MaterialGUI.ASECLIMaterialGUI" &&
                    sampler != null && sampler.PropertyName == "_AuditMask" &&
                    sampler.PropertyInspectorName == "验证遮罩" && sampler.AutoRegister &&
                    strength != null && strength.PropertyName == "_AuditStrength" &&
                    strength.PropertyInspectorName == "验证强度" &&
                    casterWorld != null &&
                    graph.CurrentMasterNode.GetInputPortByUniqueId(2).IsConnectedTo(casterWorld.UniqueId, 0) &&
                    graph.CurrentMasterNode.GetInputPortByUniqueId(3).IsConnectedTo(strength.UniqueId, 0);
            }}
            var expression = graph.AllNodes.Find(n => n is AmplifyShaderEditor.CustomExpressionNode) as AmplifyShaderEditor.CustomExpressionNode;
            var world = graph.AllNodes.Find(n => n is AmplifyShaderEditor.WorldPosInputsNode);
            var texture = graph.AllNodes.Find(n => n is AmplifyShaderEditor.TexturePropertyNode) as AmplifyShaderEditor.TexturePropertyNode;
            var uv = graph.AllNodes.Find(n => n is AmplifyShaderEditor.TextureCoordinatesNode);
            return master.CurrentInspector == "ASECLI.MaterialGUI.ASECLIMaterialGUI" &&
                expression != null && world != null && texture != null && uv != null &&
                texture.PropertyName == "_GroundMask" && texture.PropertyInspectorName == "地面遮罩" &&
                expression.InputPorts.Count == 2 &&
                expression.InputPorts[0].IsConnectedTo(world.UniqueId, 0) &&
                expression.InputPorts[1].IsConnectedTo(uv.UniqueId, 0) &&
                graph.CurrentMasterNode.GetInputPortByUniqueId(2).IsConnectedTo(expression.UniqueId, 0);
        }}
        finally
        {{
            AmplifyShaderEditor.UIUtils.CurrentWindow = previous;
            if (win != null) {{ win.Close(); Object.DestroyImmediate(win); }}
        }}
    }}
}}
'''
