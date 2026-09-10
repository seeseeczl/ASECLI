"""ASE -> sgcli.native.v2 export contract tests.

The node rows are generated from ASECLI's runtime-observed ASE 1.9.1.09
schemas; the Master row and wire ordering match real ASE Editor serialization.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from asecli.cli.commands import CliError
from asecli.cli.export_sg_command import cmd_export_sg
from asecli.export_sg import (
    ExportError,
    URP_UNLIT_GUID,
    bind_configured_ports,
    build_candidate,
    validate_schema,
)
from asecli.schema import schema_for

def _node(node_type: str, node_id: int, position: str, *, precision: str = "Inherit") -> list[str]:
    schema = schema_for(node_type)
    assert schema is not None
    return ["Node", node_type, str(node_id), position, precision, "False", *schema["fields"]]

def _master(node_id: int = 1, pass_name: str = "Forward") -> list[str]:
    return [
        "Node", "AmplifyShaderEditor.TemplateMultiPassMasterNode", str(node_id), "0,0", "Float", "False",
        "True", "-1", "2", "UnityEditor.ShaderGraphUnlitGUI", "0", "1", "Export Test",
        URP_UNLIT_GUID, "True", pass_name, "UniversalMaterialType=Unlit", "RenderType=Opaque",
        "Standard", "3", "Surface", "0", "0", "  Blend", "0", "0", "Two Sided", "1", "0",
        "Forward Only", "0", "0",
        "Cast Shadows", "1", "0", "  Use Shadow Threshold", "0", "0",
        "Receive Shadows", "1", "0", "GPU Instancing", "1", "0",
        "LOD CrossFade", "0", "0", "Built-in Fog", "1", "0",
        "Extra Pre Pass", "0", "0", "Tessellation", "0", "0",
    ]

def _shader(*nodes: list[str], wires: list[str], properties: str = "", version: str = "19109") -> str:
    return (
        'Shader "Export/Test"\n{\nProperties\n{\n' + properties + "\n}\nSubShader { Pass { Cull Back } }\n}\n"
        f"/*ASEBEGIN\nVersion={version}\n" + "\n".join(";".join(row) for row in nodes) + "\n" +
        "\n".join(wires) + "\nASEEND*/\n//CHKSM=TEST\n"
    )


@pytest.fixture
def unity_project(tmp_path: Path) -> Path:
    (tmp_path / "Assets").mkdir()
    (tmp_path / "ProjectSettings").mkdir()
    return tmp_path

def _configured_math() -> dict:
    def port(pid, input_, name, kind="Vector1"):
        return {"id": pid, "input": input_, "name": name, "type": kind}
    return {"configured_graph": {"nodes": [
        {"id": "n10", "type": "Vector1Node", "name": "Float", "position": [-400.0, 0.0], "ports": [port(1, True, "X"), port(0, False, "Out")]},
        {"id": "n11", "type": "AddNode", "name": "Add", "position": [-160.0, 0.0], "ports": [port(0, True, "A"), port(1, True, "B"), port(2, False, "Out")]},
        {"id": "block", "type": "BlockNode", "name": "Base Color", "ports": [port(0, True, "Base Color", "Vector3")]},
    ]}}

def test_nonzero_default_is_bound_to_real_sg_port(unity_project: Path):
    value = _node("AmplifyShaderEditor.RangedFloatNode", 10, "-400,0", precision="Float")
    value[19] = "0.375"
    add = _node("AmplifyShaderEditor.SimpleAddOpNode", 11, "-160,0")
    source = unity_project / "scalar.shader"
    source.write_text(_shader(value, add, _master(), wires=[
        "WireConnection;11;0;10;0", "WireConnection;1;2;11;0",
    ]), encoding="utf-8")

    candidate, report, nodes, edges = build_candidate(source, unity_project)
    spec = bind_configured_ports(candidate, report, nodes, edges, _configured_math())
    assert spec["nodes"][0]["inputs"] == {"1": 0.375}
    assert spec["nodes"][1]["inputs"] == {"1": 0.0}
    assert spec["connections"] == [
        {"from": ["ase_10", 0], "to": ["ase_11", 0]},
        {"from": ["ase_11", 2], "to": ["SurfaceDescription.BaseColor", 0]},
    ]
    validate_schema(spec, None)

def test_property_preserves_range_display_default_and_exposure(unity_project: Path):
    value = _node("AmplifyShaderEditor.RangedFloatNode", 10, "-400,0")
    value[6:9] = ["Property", "_Gain", "增益"]
    source = unity_project / "property.shader"
    source.write_text(_shader(value, _master(), wires=["WireConnection;1;2;10;0"], properties='    _Gain("增益", Range(-2, 4)) = 1.25'), encoding="utf-8")
    candidate, _, _, _ = build_candidate(source, unity_project)
    assert candidate["properties"] == [{
        "name": "_Gain", "type": "float", "display_name": "增益",
        "default": 1.25, "exposed": True, "range": [-2.0, 4.0],
    }]
    assert candidate["nodes"][0]["type"] == "property"


@pytest.mark.parametrize(("node_type", "property_type", "expected"), [
    ("AmplifyShaderEditor.Vector2Node", "vector2", [0.1, 0.25]),
    ("AmplifyShaderEditor.Vector3Node", "vector3", [0.1, 0.25, 0.75]),
])
def test_vector_property_uses_ase_dimension_and_compiled_default(
    unity_project: Path, node_type: str, property_type: str, expected: list[float],
):
    value = _node(node_type, 10, "-400,0", precision="Half")
    value[6:9] = ["Property", "_Direction", "方向"]
    source = unity_project / f"{property_type}.shader"
    source.write_text(_shader(value, _master(), wires=["WireConnection;1;2;10;0"],
        properties='    _Direction("方向", Vector) = (0.1, 0.25, 0.75, 1.0)'), encoding="utf-8")

    candidate, _, _, _ = build_candidate(source, unity_project)
    assert candidate["properties"] == [{
        "name": "_Direction", "type": property_type, "display_name": "方向",
        "default": expected, "exposed": True, "settings": {"precision": "Half"},
    }]

def test_source_hash_uses_original_bytes(unity_project: Path):
    value = _node("AmplifyShaderEditor.RangedFloatNode", 10, "-400,0")
    source = unity_project / "crlf.shader"
    raw = _shader(value, _master(), wires=["WireConnection;1;2;10;0"]).replace("\n", "\r\n").encode()
    source.write_bytes(raw)

    _, report, _, _ = build_candidate(source, unity_project)
    assert report["source"]["sha256"] == hashlib.sha256(raw).hexdigest()

def test_bundled_schema_matches_sgcli_contract():
    bundled = Path(__file__).parents[1] / "src/asecli/sg_export/sgcli.native.v2.schema.json"
    receiver = Path(__file__).parents[2] / "SGCLI/schemas/sgcli.native.v2.schema.json"
    assert hashlib.sha256(bundled.read_bytes()).digest() == hashlib.sha256(receiver.read_bytes()).digest()

def test_vector_default_uses_configured_component_ports(unity_project: Path):
    value = _node("AmplifyShaderEditor.Vector3Node", 10, "-400,0")
    value[19] = "0.1,0.25,0.75"
    source = unity_project / "vector.shader"
    source.write_text(_shader(value, _master(), wires=["WireConnection;1;2;10;0"]), encoding="utf-8")
    candidate, report, nodes, edges = build_candidate(source, unity_project)
    configured = {"configured_graph": {"nodes": [
        {"id": "v", "type": "Vector3Node", "name": "Vector 3", "position": [-400.0, 0.0], "ports": [
            {"id": -3, "input": True, "name": "X", "type": "Vector1"},
            {"id": -2, "input": True, "name": "Y", "type": "Vector1"},
            {"id": -1, "input": True, "name": "Z", "type": "Vector1"},
            {"id": 8, "input": False, "name": "Out", "type": "Vector3"},
        ]},
        {"id": "block", "type": "BlockNode", "name": "Base Color", "ports": [{"id": 0, "input": True, "name": "Base Color", "type": "Vector3"}]},
    ]}}
    spec = bind_configured_ports(candidate, report, nodes, edges, configured)
    assert spec["nodes"][0]["inputs"] == {"-3": 0.1, "-2": 0.25, "-1": 0.75}
    assert spec["connections"][0]["from"] == ["ase_10", 8]
    validate_schema(spec, None)

def test_runtime_catalog_port_suffixes_and_full_block_names_are_bound(unity_project: Path):
    value = _node("AmplifyShaderEditor.RangedFloatNode", 10, "-400,0")
    source = unity_project / "runtime-names.shader"
    source.write_text(_shader(value, _master(), wires=["WireConnection;1;2;10;0"]), encoding="utf-8")
    candidate, report, nodes, edges = build_candidate(source, unity_project)
    configured = {"configured_graph": {"nodes": [
        {"id": "value", "type": "Vector1Node", "name": "Float", "position": [-400.0, 0.0], "ports": [
            {"id": 1, "input": True, "name": "X(1)", "type": "Vector1"},
            {"id": 0, "input": False, "name": "Out(1)", "type": "Vector1"},
        ]},
        {"id": "block", "type": "BlockNode", "name": "SurfaceDescription.BaseColor", "ports": [
            {"id": 0, "input": True, "name": "Base Color(3)", "type": "Vector3"},
        ]},
    ]}}
    spec = bind_configured_ports(candidate, report, nodes, edges, configured)
    assert spec["connections"] == [{"from": ["ase_10", 0], "to": ["SurfaceDescription.BaseColor", 0]}]


def test_texture_property_sample_expands_and_preserves_null(unity_project: Path):
    sampler = _node("AmplifyShaderEditor.SamplerNode", 10, "-400,0")
    sampler[6:9] = ["Property", "_MainTex", "主贴图"]
    source = unity_project / "texture.shader"
    source.write_text(_shader(sampler, _master(), wires=["WireConnection;1;2;10;0"], properties='    _MainTex("主贴图", 2D) = "white" {}'), encoding="utf-8")
    candidate, report, nodes, edges = build_candidate(source, unity_project)
    assert candidate["properties"][0]["default"] is None
    assert [node["type"] for node in candidate["nodes"]] == ["property", "sample-texture"]
    assert any(edge.source_id == "ase_10_property" and edge.target_id == "ase_10" for edge in edges)
    configured = {"configured_graph": {"nodes": [
        {"type": "PropertyNode", "name": "Property", "position": [-400.0, 0.0],
         "ports": [{"id": -9, "input": False, "name": "主贴图(T2)", "type": "Texture2D"}]},
        {"type": "SampleTexture2DNode", "name": "Sample Texture 2D", "position": [-160.0, 0.0],
         "ports": [
             {"id": 0, "input": False, "name": "RGBA(4)", "type": "Vector4"},
             {"id": 4, "input": False, "name": "R(1)", "type": "Vector1"},
             {"id": 5, "input": False, "name": "G(1)", "type": "Vector1"},
             {"id": 6, "input": False, "name": "B(1)", "type": "Vector1"},
             {"id": 7, "input": False, "name": "A(1)", "type": "Vector1"},
             {"id": 1, "input": True, "name": "Texture(T2)", "type": "Texture2D"},
         ]},
        {"type": "BlockNode", "name": "SurfaceDescription.BaseColor",
         "ports": [{"id": 0, "input": True, "name": "Base Color(3)", "type": "Vector3"}]},
    ]}}
    spec = bind_configured_ports(candidate, report, nodes, edges, configured)
    assert {tuple(row["from"] + row["to"]) for row in spec["connections"]} == {
        ("ase_10", 0, "SurfaceDescription.BaseColor", 0),
        ("ase_10_property", -9, "ase_10", 1),
    }


def test_alpha_clip_enables_target_option(unity_project: Path):
    value = _node("AmplifyShaderEditor.RangedFloatNode", 10, "-400,0")
    source = unity_project / "clip.shader"
    source.write_text(_shader(value, _master(), wires=["WireConnection;1;4;10;0"]), encoding="utf-8")
    candidate, _, _, _ = build_candidate(source, unity_project)
    assert candidate["target"]["options"] == {
        "alphaClip": True, "castShadows": True, "receiveShadows": True,
        "supportsLodCrossFade": False,
    }


def test_active_master_options_map_transparency_blend_and_two_sided(unity_project: Path):
    value = _node("AmplifyShaderEditor.RangedFloatNode", 10, "-400,0")
    master = _master()
    master[master.index("Surface") + 1] = "1"
    master[master.index("  Blend") + 1] = "2"
    master[master.index("Two Sided") + 1] = "0"
    source = unity_project / "transparent.shader"
    source.write_text(_shader(value, master, wires=["WireConnection;1;3;10;0"]), encoding="utf-8")

    candidate, _, _, _ = build_candidate(source, unity_project)
    assert candidate["target"] == {
        "model": "Unlit", "surface": "Transparent", "blend": "Additive", "two_sided": True,
        "options": {"castShadows": True, "receiveShadows": True, "supportsLodCrossFade": False},
    }


def test_19602_exact_standard_unlit_pass_set_is_accepted(unity_project: Path):
    value = _node("AmplifyShaderEditor.RangedFloatNode", 10, "-400,0")
    passes = [
        "ExtraPrePass", "Forward", "ShadowCaster", "DepthOnly", "Meta", "Universal2D",
        "SceneSelectionPass", "ScenePickingPass", "DepthNormals", "DepthNormalsOnly",
    ]
    masters = [_master(100 + index, pass_name) for index, pass_name in enumerate(passes)]
    forward_id = 100 + passes.index("Forward")
    source = unity_project / "standard-19602.shader"
    source.write_text(_shader(value, *masters, wires=[f"WireConnection;{forward_id};2;10;0"],
                              version="19602"), encoding="utf-8")

    candidate, report, _, _ = build_candidate(source, unity_project)
    assert candidate["target"]["model"] == "Unlit"
    template = next(row for row in report["mappings"] if row["kind"] == "certified_template_pass_set")
    assert set(template["passes"]) == set(passes)


@pytest.mark.parametrize("mutation", ["unexpected", "duplicate"])
def test_nonstandard_19602_pass_set_fails_closed(unity_project: Path, mutation: str):
    value = _node("AmplifyShaderEditor.RangedFloatNode", 10, "-400,0")
    passes = [
        "ExtraPrePass", "Forward", "ShadowCaster", "DepthOnly", "Meta", "Universal2D",
        "SceneSelectionPass", "ScenePickingPass", "DepthNormals", "DepthNormalsOnly",
    ]
    passes[-1] = "CustomPass" if mutation == "unexpected" else "Forward"
    masters = [_master(100 + index, pass_name) for index, pass_name in enumerate(passes)]
    source = unity_project / f"bad-pass-{mutation}.shader"
    source.write_text(_shader(value, *masters, wires=["WireConnection;101;2;10;0"],
                              version="19602"), encoding="utf-8")

    with pytest.raises(ExportError) as raised:
        build_candidate(source, unity_project)
    assert "MULTIPASS_UNSUPPORTED" in {row["code"] for row in raised.value.report["diagnostics"]}


def test_connection_to_inactive_standard_pass_fails_closed(unity_project: Path):
    first = _node("AmplifyShaderEditor.RangedFloatNode", 10, "-400,0")
    second = _node("AmplifyShaderEditor.RangedFloatNode", 11, "-400,100")
    passes = [
        "ExtraPrePass", "Forward", "ShadowCaster", "DepthOnly", "Meta", "Universal2D",
        "SceneSelectionPass", "ScenePickingPass", "DepthNormals", "DepthNormalsOnly",
    ]
    masters = [_master(100 + index, pass_name) for index, pass_name in enumerate(passes)]
    source = unity_project / "connected-inactive.shader"
    source.write_text(_shader(first, second, *masters, wires=[
        "WireConnection;101;2;10;0", "WireConnection;102;2;11;0",
    ], version="19602"), encoding="utf-8")

    with pytest.raises(ExportError) as raised:
        build_candidate(source, unity_project)
    codes = {row["code"] for row in raised.value.report["diagnostics"]}
    assert {"MASTER_AMBIGUOUS", "MULTIPASS_UNSUPPORTED"} <= codes


def test_mzgui_metadata_is_reported_as_degradation_only(unity_project: Path):
    value = _node("AmplifyShaderEditor.RangedFloatNode", 10, "-400,0")
    value[6:9] = ["Property", "_Gain", "增益"]
    source = unity_project / "mzgui.shader"
    source.write_text(_shader(value, _master(), wires=["WireConnection;1;2;10;0"],
        properties='    [FoldoutMzgui(基础)] [TooltipMzgui(控制增益)] _Gain("增益", Float) = 1.25'),
        encoding="utf-8")

    candidate, report, _, _ = build_candidate(source, unity_project)
    assert candidate["properties"][0]["name"] == "_Gain"
    assert all("metadata" not in row for row in candidate["properties"])
    assert report["equivalence"]["status"] == "degraded"
    assert report["degradations"][0]["code"] == "INSPECTOR_METADATA_NOT_MIGRATED"


def test_default_uv_and_split_nodes_decode_without_guessing(unity_project: Path):
    uv = _node("AmplifyShaderEditor.TextureCoordinatesNode", 10, "-500,0")
    split = _node("AmplifyShaderEditor.BreakToComponentsNode", 11, "-250,0")
    source = unity_project / "uv.shader"
    source.write_text(_shader(uv, split, _master(), wires=[
        "WireConnection;11;0;10;0", "WireConnection;1;2;11;0",
    ]), encoding="utf-8")
    candidate, _, nodes, edges = build_candidate(source, unity_project)
    assert [row["type"] for row in candidate["nodes"]] == ["uv", "split"]
    assert nodes[1].defaults == {}
    assert [(edge.source_id, edge.target_id) for edge in edges] == [
        ("ase_10", "ase_11"), ("ase_11", "SurfaceDescription.BaseColor"),
    ]


def test_local_var_is_folded_to_real_source(unity_project: Path):
    value = _node("AmplifyShaderEditor.RangedFloatNode", 10, "-400,0")
    register = ["Node", "AmplifyShaderEditor.RegisterLocalVarNode", "20", "-200,0", "Inherit", "False", "Local", "", "", "", "", "", "", "", "", "FLOAT"]
    getter = ["Node", "AmplifyShaderEditor.GetLocalVarNode", "21", "0,0", "Inherit", "False", "20", "Local", "", "", "", "", "", "", "FLOAT"]
    source = unity_project / "local.shader"
    source.write_text(_shader(value, register, getter, _master(), wires=[
        "WireConnection;20;0;10;0", "WireConnection;1;2;21;0",
    ]), encoding="utf-8")
    candidate, _, _, edges = build_candidate(source, unity_project)
    assert [node["id"] for node in candidate["nodes"]] == ["ase_10"]
    assert [(e.source_id, e.target_id) for e in edges] == [("ase_10", "SurfaceDescription.BaseColor")]


def test_duplicate_input_and_invalid_local_var_fail_closed(unity_project: Path):
    first = _node("AmplifyShaderEditor.RangedFloatNode", 10, "-400,0")
    second = _node("AmplifyShaderEditor.RangedFloatNode", 11, "-400,100")
    add = _node("AmplifyShaderEditor.SimpleAddOpNode", 12, "-200,0")
    getter = ["Node", "AmplifyShaderEditor.GetLocalVarNode", "21", "0,0", "Inherit", "False"]
    source = unity_project / "ambiguous.shader"
    source.write_text(_shader(first, second, add, getter, _master(), wires=[
        "WireConnection;12;0;10;0", "WireConnection;12;0;11;0", "WireConnection;1;2;21;0",
    ]), encoding="utf-8")
    with pytest.raises(ExportError) as raised:
        build_candidate(source, unity_project)
    codes = {row["code"] for row in raised.value.report["diagnostics"]}
    assert {"DUPLICATE_INPUT", "SOURCE_INVALID"} <= codes
