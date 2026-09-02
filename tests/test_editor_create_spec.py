"""REG-0026: EditorGraphSpec v1 is strict before any MCP call."""

from __future__ import annotations

import json

import pytest

from asecli.bridge.editor_spec import EditorGraphSpec, SpecError, load_editor_graph_spec, route_create_backend


TEMPLATE_GUID = "2992e84f91cbeb14eab234972e07ea9d"


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


def receiver_spec() -> dict:
    return {
        "version": 1,
        "template": {"guid": TEMPLATE_GUID, "shader_name": "Tests/EditorReceiver"},
        "nodes": [
            {"alias": "world", "kind": "node", "type": "WorldPosInputsNode", "position": [-850, -80]},
            {
                "alias": "ground_mask",
                "kind": "property",
                "type": "TexturePropertyNode",
                "position": [-930, 300],
                "property_name": "_GroundMask",
                "inspector_name": "Ground Mask",
                "parameter_type": "Property",
            },
            {"alias": "uv", "kind": "node", "type": "TextureCoordinatesNode", "position": [-930, 500]},
            {
                "alias": "expr",
                "kind": "custom_expression",
                "position": [-430, 10],
                "name": "Vehicle Local Shadow Core",
                "code": "return float4(WorldPosition.x, GroundMaskUV.y, 0, tex2D(GroundMaskTex, GroundMaskUV).r);",
                "output_type": "FLOAT4",
                "inputs": [
                    {"name": "WorldPosition", "type": "FLOAT3"},
                    {"name": "GroundMaskTex", "type": "SAMPLER2D"},
                    {"name": "GroundMaskUV", "type": "FLOAT2"},
                ],
            },
        ],
        "connections": [
            {"from": {"node": "world", "port": 0}, "to": {"node": "expr", "port": 0}},
            {"from": {"node": "ground_mask", "port": 0}, "to": {"node": "expr", "port": 1}},
            {"from": {"node": "uv", "port": 0}, "to": {"node": "expr", "port": 2}},
            {"from": {"node": "expr", "port": 0}, "to": {"node": "master", "port": 2}},
        ],
    }


def test_caster_and_receiver_specs_are_canonical_and_editor_routed(tmp_path):
    caster = EditorGraphSpec.from_dict(caster_spec())
    receiver_path = tmp_path / "receiver.json"
    receiver_path.write_text(json.dumps(receiver_spec()), encoding="utf-8")
    receiver = load_editor_graph_spec(receiver_path)

    assert caster.version == 1
    assert receiver.nodes[-1].kind == "custom_expression"
    assert receiver.nodes[-1].inputs[1].type == "SAMPLER2D"
    assert route_create_backend("auto", caster) == "editor"
    assert route_create_backend("auto", None) == "text"
    assert route_create_backend("editor", caster) == "editor"


@pytest.mark.parametrize(
    "mutate, match",
    [
        (lambda spec: spec.update({"csharp": "System.IO.File.Delete('x')"}), "unknown"),
        (lambda spec: spec["nodes"][0].update({"reflection_field": "m_anything"}), "unknown"),
        (lambda spec: spec["nodes"][0].update({"type": "System.IO.File"}), "unknown"),
        (lambda spec: spec["nodes"][0].update({"alias": "master"}), "reserved"),
    ],
)
def test_unknown_code_reflection_type_and_reserved_alias_are_rejected(mutate, match):
    spec = caster_spec()
    mutate(spec)
    with pytest.raises(SpecError, match=match):
        EditorGraphSpec.from_dict(spec)


@pytest.mark.parametrize("code", ["return 1@$;", "using UnityEditor; return 1;", "System.Reflection.Assembly.Load(\"x\");"])
def test_custom_expression_rejects_ase_delimiters_and_csharp_markers(code):
    spec = receiver_spec()
    spec["nodes"][-1]["code"] = code
    with pytest.raises(SpecError, match="code"):
        EditorGraphSpec.from_dict(spec)


def test_duplicate_alias_input_name_and_destination_port_are_rejected():
    spec = receiver_spec()
    spec["nodes"][1]["alias"] = "world"
    with pytest.raises(SpecError, match="alias"):
        EditorGraphSpec.from_dict(spec)

    spec = receiver_spec()
    spec["nodes"][-1]["inputs"][1]["name"] = "WorldPosition"
    with pytest.raises(SpecError, match="input name"):
        EditorGraphSpec.from_dict(spec)

    spec = receiver_spec()
    spec["connections"].append(
        {"from": {"node": "uv", "port": 0}, "to": {"node": "expr", "port": 0}}
    )
    with pytest.raises(SpecError, match="destination"):
        EditorGraphSpec.from_dict(spec)


@pytest.mark.parametrize(
    "first_kind, second_kind",
    [("property", "property"), ("property", "sampler"), ("sampler", "sampler")],
)
def test_duplicate_property_names_are_rejected_across_property_node_kinds(first_kind, second_kind):
    spec = receiver_spec()
    property_node = spec["nodes"][1]
    property_node["kind"] = first_kind
    if first_kind == "sampler":
        property_node.pop("type")
    duplicate = {
        "alias": "duplicate_property",
        "kind": second_kind,
        "position": [-700, 300],
        "property_name": "_GroundMask",
        "inspector_name": "Duplicate Ground Mask",
        "parameter_type": "Property",
    }
    if second_kind == "property":
        duplicate["type"] = "TexturePropertyNode"
    spec["nodes"].append(duplicate)

    with pytest.raises(SpecError, match="property_name"):
        EditorGraphSpec.from_dict(spec)


def test_invalid_port_type_and_missing_alias_are_rejected():
    spec = receiver_spec()
    spec["nodes"][-1]["inputs"][0]["type"] = "CSharpObject"
    with pytest.raises(SpecError, match="type"):
        EditorGraphSpec.from_dict(spec)

    spec = receiver_spec()
    spec["connections"][0]["from"]["node"] = "missing"
    with pytest.raises(SpecError, match="unknown node alias"):
        EditorGraphSpec.from_dict(spec)


@pytest.mark.parametrize(
    "endpoint, port, match",
    [
        ("from", 63, "source port"),
        ("to", 63, "destination port"),
    ],
)
def test_nonexistent_ports_are_rejected_before_editor_execution(endpoint, port, match):
    spec = caster_spec()
    spec["connections"][0][endpoint]["port"] = port
    with pytest.raises(SpecError, match=match):
        EditorGraphSpec.from_dict(spec)


def test_wrong_port_direction_and_incompatible_types_are_rejected():
    spec = receiver_spec()
    spec["connections"][0]["from"] = {"node": "ground_mask", "port": 7}
    with pytest.raises(SpecError, match="source port"):
        EditorGraphSpec.from_dict(spec)

    spec = receiver_spec()
    spec["connections"][0]["from"] = {"node": "ground_mask", "port": 0}
    with pytest.raises(SpecError, match="incompatible port types"):
        EditorGraphSpec.from_dict(spec)


def test_unknown_template_cannot_claim_a_master_port_contract():
    spec = caster_spec()
    spec["template"]["guid"] = "0" * 32
    with pytest.raises(SpecError, match="master-port contract"):
        EditorGraphSpec.from_dict(spec)


def test_expected_manifest_includes_template_identity():
    spec = EditorGraphSpec.from_dict(caster_spec())
    assert spec.expected_manifest()["template"] == {
        "guid": TEMPLATE_GUID,
        "shader_name": "Tests/EditorCaster",
    }


def test_property_inspector_name_accepts_chinese_display_name():
    raw = caster_spec()
    raw["nodes"][0]["inspector_name"] = "投射遮罩"

    spec = EditorGraphSpec.from_dict(raw)

    assert spec.nodes[0].inspector_name == "投射遮罩"
    assert spec.expected_manifest()["nodes"][0]["inspector_name"] == "投射遮罩"


def test_v2_requires_chinese_display_name_and_chinese_help_for_every_property():
    raw = caster_spec()
    raw["version"] = 2
    raw["nodes"][0]["inspector_name"] = "投射遮罩"
    raw["nodes"][0]["help"] = "控制投射遮罩贴图；白色区域显示阴影。"

    spec = EditorGraphSpec.from_dict(raw)

    assert spec.version == 2
    assert spec.nodes[0].help == "控制投射遮罩贴图；白色区域显示阴影。"
    assert spec.editor_payload("Assets/Caster.shader", "Assets/ASECLI-Temp-Caster.shader")["version"] == 1

    missing_help = caster_spec()
    missing_help["version"] = 2
    missing_help["nodes"][0]["inspector_name"] = "投射遮罩"
    with pytest.raises(SpecError, match="help"):
        EditorGraphSpec.from_dict(missing_help)

    english_display = caster_spec()
    english_display["version"] = 2
    english_display["nodes"][0]["help"] = "控制投射遮罩贴图。"
    with pytest.raises(SpecError, match="inspector_name.*Chinese"):
        EditorGraphSpec.from_dict(english_display)

    english_help = caster_spec()
    english_help["version"] = 2
    english_help["nodes"][0]["inspector_name"] = "投射遮罩"
    english_help["nodes"][0]["help"] = "Controls the caster mask."
    with pytest.raises(SpecError, match="help.*Chinese"):
        EditorGraphSpec.from_dict(english_help)
