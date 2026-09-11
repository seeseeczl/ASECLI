"""Direct ASECLI -> sgcli.native.v3 export contract tests."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from types import SimpleNamespace

import pytest

from asecli.bridge.editor_spec import (
    SpecError,
    load_editor_graph_spec,
)
from asecli.bridge._editor_spec_io import load_editor_graph_spec_with_sha256
from asecli.cli.commands import CliError
from asecli.cli.export_sg_command import _write_pair, cmd_export_sg
from asecli.core.model import parse_node_line
from asecli.export_sg import ExportError, URP_UNLIT_GUID, bind_named_ports, build_candidate
from asecli.schema import schema_for
from asecli.sg_export.nodes import convert_node
from asecli.sg_export.sources import sampler_texture_guid


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
        "Forward Only", "0", "0", "Cast Shadows", "1", "0", "  Use Shadow Threshold", "0", "0",
        "Receive Shadows", "1", "0", "GPU Instancing", "1", "0", "LOD CrossFade", "0", "0",
        "Built-in Fog", "1", "0", "Extra Pre Pass", "0", "0", "Tessellation", "0", "0",
    ]


def _shader(*nodes: list[str], wires: list[str], properties: str = "", version: str = "19109") -> str:
    return (
        'Shader "Export/Test"\n{\nProperties\n{\n' + properties + "\n}\nSubShader { Pass { Cull Back } }\n}\n"
        f"/*ASEBEGIN\nVersion={version}\n" + "\n".join(";".join(row) for row in nodes) + "\n"
        + "\n".join(wires) + "\nASEEND*/\n//CHKSM=TEST\n"
    )


@pytest.fixture
def unity_project(tmp_path: Path) -> Path:
    (tmp_path / "Assets").mkdir()
    (tmp_path / "ProjectSettings").mkdir()
    return tmp_path


def test_named_v3_binding_preserves_defaults_and_connections(unity_project: Path):
    value = _node("AmplifyShaderEditor.RangedFloatNode", 10, "-400,0", precision="Float")
    value[19] = "0.375"
    add = _node("AmplifyShaderEditor.SimpleAddOpNode", 11, "-160,0")
    source = unity_project / "Assets" / "scalar.shader"
    source.write_text(_shader(value, add, _master(), wires=[
        "WireConnection;11;0;10;0", "WireConnection;1;2;11;0",
    ]), encoding="utf-8")

    candidate, report, nodes, edges = build_candidate(source, unity_project)
    spec = bind_named_ports(candidate, report, nodes, edges)
    assert spec["schema"] == "sgcli.native.v3"
    assert spec["nodes"][0]["inputs"] == {"X": 0.375}
    assert spec["nodes"][1]["inputs"] == {"B": 0.0}
    assert spec["connections"] == [
        {"from": ["ase_10", "Out"], "to": ["ase_11", "A"]},
        {"from": ["ase_11", "Out"], "to": ["SurfaceDescription.BaseColor", "Base Color"]},
    ]


def test_command_writes_canonical_pair_without_sgcli_runtime(unity_project: Path):
    value = _node("AmplifyShaderEditor.RangedFloatNode", 10, "-400,0")
    source = unity_project / "Assets" / "WaveNoise.shader"
    source.write_text(
        _shader(value, _master(), wires=["WireConnection;1;2;10;0"]),
        encoding="utf-8",
    )
    out = unity_project / "out"
    args = SimpleNamespace(
        file=str(source), out_dir=str(out), target_project=None, name=None, asset_map=None
    )
    result = cmd_export_sg(args)
    spec_path = out / "WaveNoise.asecli-to-sgcli.spec.json"
    report_path = out / "WaveNoise.asecli-to-sgcli.report.json"
    receipt_path = out / "WaveNoise.asecli-to-sgcli.receipt.json"
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert result["spec_json"] == str(spec_path)
    assert result["report_json"] == str(report_path)
    assert result["receipt_json"] == str(receipt_path)
    assert "graph_json" not in result
    assert spec["schema"] == "sgcli.native.v3"
    assert not ({"report", "source", "metadata", "graph"} & set(spec))
    assert report["schema"] == "sgcli.shader-conversion-report.v1"
    assert report["target"]["sha256"] == hashlib.sha256(spec_path.read_bytes()).hexdigest()
    assert report["conversion_success"] is False
    assert report["visual_equivalent"] is False
    assert report["evidence"]["producer_schema_validated"] == "passed"
    assert report["evidence"]["consumer_loaded"] == "not_run"
    assert report["source"]["source_snapshot_sha256"] == report["source"]["source_recheck_sha256"]
    receipt = json.loads(receipt_path.read_text())
    assert receipt["complete"] is True
    assert receipt["spec"]["committed"] is True
    assert receipt["report"]["committed"] is True
    with pytest.raises(CliError) as raised:
        cmd_export_sg(args)
    assert raised.value.code == "WRITE_CONFLICT"


def test_failure_writes_report_but_no_partial_spec(unity_project: Path):
    unknown = ["Node", "AmplifyShaderEditor.CustomExpressionNode", "99", "-400,0", "Inherit", "False"]
    source = unity_project / "Assets" / "unsupported.shader"
    source.write_text(
        _shader(unknown, _master(), wires=["WireConnection;1;2;99;0"]),
        encoding="utf-8",
    )
    out = unity_project / "out"
    args = SimpleNamespace(
        file=str(source), out_dir=str(out), target_project=None, name=None, asset_map=None
    )
    with pytest.raises(CliError) as raised:
        cmd_export_sg(args)
    assert raised.value.code == "SG_EXPORT_BLOCKED"
    assert not (out / "unsupported.asecli-to-sgcli.spec.json").exists()
    report = json.loads(
        (out / "unsupported.asecli-to-sgcli.report.json").read_text(encoding="utf-8")
    )
    assert report["conversion_success"] is False
    assert report["degradations"]


def test_initial_source_read_failure_is_structured(monkeypatch, unity_project: Path):
    source = unity_project / "Assets" / "unreadable.shader"
    source.write_text("placeholder", encoding="utf-8")
    real_read_bytes = Path.read_bytes

    def fail_source_read(path):
        if path == source:
            raise OSError("injected read failure")
        return real_read_bytes(path)

    monkeypatch.setattr(Path, "read_bytes", fail_source_read)
    args = SimpleNamespace(
        file=str(source), out_dir=str(unity_project / "out"),
        target_project=None, name=None, asset_map=None,
    )
    with pytest.raises(CliError) as raised:
        cmd_export_sg(args)
    assert raised.value.code == "SG_EXPORT_BLOCKED"
    assert "could not read source Shader" in str(raised.value)


def test_second_file_publish_failure_leaves_only_report(monkeypatch, tmp_path: Path):
    spec_path = tmp_path / "Graph.asecli-to-sgcli.spec.json"
    report_path = tmp_path / "Graph.asecli-to-sgcli.report.json"
    real_link = os.link

    def fail_spec_link(source, destination):
        if Path(destination) == spec_path:
            raise OSError("injected spec publish failure")
        return real_link(source, destination)

    monkeypatch.setattr("asecli.cli.conversion_output.os.link", fail_spec_link)
    with pytest.raises(CliError) as raised:
        _write_pair(spec_path, {"schema": "sgcli.native.v3"}, report_path, {"schema": "report"})
    assert raised.value.code == "WRITE_PARTIAL"
    assert report_path.is_file()
    assert not spec_path.exists()
    receipt_path = tmp_path / "Graph.asecli-to-sgcli.receipt.json"
    receipt = json.loads(receipt_path.read_text())
    assert receipt["complete"] is False
    assert receipt["report"]["committed"] is True
    assert receipt["spec"]["committed"] is False


def test_receipt_publish_failure_reports_committed_pair(monkeypatch, tmp_path: Path):
    spec_path = tmp_path / "Graph.asecli-to-sgcli.spec.json"
    report_path = tmp_path / "Graph.asecli-to-sgcli.report.json"
    receipt_path = tmp_path / "Graph.asecli-to-sgcli.receipt.json"
    real_link = os.link

    def fail_receipt_link(source, destination):
        if Path(destination) == receipt_path:
            raise OSError("injected receipt publish failure")
        return real_link(source, destination)

    monkeypatch.setattr("asecli.cli.conversion_output.os.link", fail_receipt_link)
    with pytest.raises(CliError) as raised:
        _write_pair(spec_path, {"schema": "sgcli.native.v3"}, report_path, {"schema": "report"})
    assert raised.value.code == "WRITE_PARTIAL"
    assert spec_path.is_file()
    assert report_path.is_file()
    assert not receipt_path.exists()


@pytest.mark.parametrize(
    "phase",
    [
        "after conversion",
        "before report construction",
        "after report construction",
        "before publication",
    ],
)
def test_source_change_at_each_export_boundary_leaves_only_report(
    monkeypatch, unity_project: Path, phase: str
):
    value = _node("AmplifyShaderEditor.RangedFloatNode", 10, "-400,0")
    source = unity_project / "Assets" / "WaveNoise.shader"
    source.write_text(
        _shader(value, _master(), wires=["WireConnection;1;2;10;0"]),
        encoding="utf-8",
    )
    out = unity_project / "out"
    args = SimpleNamespace(
        file=str(source), out_dir=str(out), target_project=None, name=None, asset_map=None
    )
    import asecli.cli.export_sg_command as command

    original = command._assert_source_unchanged

    def mutate_at_boundary(path, snapshot, current_phase):
        if current_phase == phase:
            path.write_bytes(snapshot + b"\n")
        return original(path, snapshot, current_phase)

    monkeypatch.setattr(command, "_assert_source_unchanged", mutate_at_boundary)
    with pytest.raises(CliError) as raised:
        cmd_export_sg(args)
    assert raised.value.code == "SG_EXPORT_BLOCKED"
    assert not (out / "WaveNoise.asecli-to-sgcli.spec.json").exists()
    report = json.loads((out / "WaveNoise.asecli-to-sgcli.report.json").read_text())
    assert report["source"]["source_snapshot_sha256"] != report["source"]["source_recheck_sha256"]


def test_producer_schema_failure_leaves_only_report(monkeypatch, unity_project: Path):
    value = _node("AmplifyShaderEditor.RangedFloatNode", 10, "-400,0")
    source = unity_project / "Assets" / "WaveNoise.shader"
    source.write_text(
        _shader(value, _master(), wires=["WireConnection;1;2;10;0"]),
        encoding="utf-8",
    )
    out = unity_project / "out"
    args = SimpleNamespace(
        file=str(source), out_dir=str(out), target_project=None, name=None, asset_map=None
    )
    monkeypatch.setattr(
        "asecli.cli.export_sg_command.bind_named_ports",
        lambda *args, **kwargs: {"schema": "sgcli.native.v3", "bogus": True},
    )
    with pytest.raises(CliError) as raised:
        cmd_export_sg(args)
    assert raised.value.code == "SG_EXPORT_BLOCKED"
    assert not (out / "WaveNoise.asecli-to-sgcli.spec.json").exists()
    report = json.loads((out / "WaveNoise.asecli-to-sgcli.report.json").read_text())
    assert report["evidence"]["producer_schema_validated"] == "failed"


def test_directory_sync_failure_is_a_committed_warning(monkeypatch, tmp_path: Path):
    from asecli.cli.export_sg_command import _write_new

    monkeypatch.setattr(
        "asecli.cli.conversion_output.sync_directory",
        lambda *args: "directory sync unavailable: unsupported",
    )
    result = _write_new(tmp_path / "result.json", {"ok": True})
    assert result["committed"] is True
    assert result["warnings"] == ["directory sync unavailable: unsupported"]


def test_consumer_rejects_known_reverse_direction(tmp_path: Path):
    for suffix in ("spec", "report"):
        path = tmp_path / f"Graph.asecli-to-sgcli.{suffix}.json"
        path.write_text("{}", encoding="utf-8")
        with pytest.raises(SpecError, match="ASECLI cannot consume"):
            load_editor_graph_spec(path)


def test_consumer_hash_is_exact_input_bytes(tmp_path: Path):
    path = tmp_path / "Graph.sgcli-to-asecli.spec.json"
    raw = (
        '{"version":3,"primitives_version":1,"template":'
        '{"guid":"2992e84f91cbeb14eab234972e07ea9d","shader_name":"Hash/Test"},'
        '"nodes":[],"connections":[]}\n'
    ).encode("utf-8")
    path.write_bytes(raw)
    spec, digest = load_editor_graph_spec_with_sha256(path)
    assert spec.version == 3
    assert digest == hashlib.sha256(raw).hexdigest()


def test_unsupported_source_still_fails_closed(unity_project: Path):
    unknown = ["Node", "AmplifyShaderEditor.CustomExpressionNode", "99", "-400,0", "Inherit", "False"]
    source = unity_project / "Assets" / "unsupported.shader"
    source.write_text(
        _shader(unknown, _master(), wires=["WireConnection;1;2;99;0"]),
        encoding="utf-8",
    )
    with pytest.raises(ExportError):
        build_candidate(source, unity_project)


def test_wave_noise_node_decoders_preserve_defaults_spaces_and_expression(tmp_path: Path):
    power = parse_node_line(
        "Node;AmplifyShaderEditor.PowerNode;58;6640,428;Inherit;False;False;2;"
        "0;FLOAT;0;False;1;FLOAT;1;False;1;FLOAT;0"
    )
    power_nodes, _, _ = convert_node(power, [], {}, tmp_path, {})
    assert power_nodes[0].target_type == "power"
    assert power_nodes[0].defaults == {0: 0.0, 1: 1.0}

    world_position = parse_node_line(
        "Node;AmplifyShaderEditor.WorldPosInputsNode;40;7408,3308;Inherit;False;"
        "0;4;FLOAT3;0;FLOAT;1;FLOAT;2;FLOAT;3"
    )
    world_normal = parse_node_line(
        "Node;AmplifyShaderEditor.WorldNormalVector;60;6608,857;Inherit;False;False;1;"
        "0;FLOAT3;0,0,1;False;4;FLOAT3;0;FLOAT;1;FLOAT;2;FLOAT;3"
    )
    position_nodes, _, _ = convert_node(world_position, [], {}, tmp_path, {})
    normal_nodes, _, _ = convert_node(world_normal, [], {}, tmp_path, {})
    assert position_nodes[0].target_type == "position"
    assert position_nodes[0].settings == {"spacePopup": "World"}
    assert normal_nodes[0].target_type == "normal"
    assert normal_nodes[0].settings == {"spacePopup": "World"}

    expression = parse_node_line(
        "Node;AmplifyShaderEditor.CustomExpressionNode;31;0,0;Inherit;False;"
        "float x = A * B@$return x@;1;Create;2;"
        "True;A;FLOAT;0;In;;Inherit;False;"
        "True;B;FLOAT;1;In;;Inherit;False;"
        "Expr;True;False;0;;False;2;0;FLOAT;0;False;1;FLOAT;1;False;1;FLOAT;0"
    )
    expression_nodes, _, _ = convert_node(expression, [], {}, tmp_path, {})
    function = expression_nodes[0].function
    assert function is not None
    assert function["body"] == "float x = A * B;\nOut = x;"
    assert function["ports"] == [
        {"name": "Out", "type": "Vector1", "direction": "Output"},
        {"name": "A", "type": "Vector1", "direction": "Input"},
        {"name": "B", "type": "Vector1", "direction": "Input"},
    ]


def test_wave_noise_color_and_sampler_fields_are_relative_to_create_marker(tmp_path: Path):
    color = parse_node_line(
        "Node;AmplifyShaderEditor.ColorNode;10;3696,3097;Float;False;Property;"
        "_Color_A;第三色带;6;0;Create;False;0;0;0;True;0;False;1,1,1,0;"
        "0,0,0,0;True;True;0;6;COLOR;0;FLOAT;1;FLOAT;2;FLOAT;3;FLOAT;4;"
        "FLOAT3;5;1;[TooltipMzgui(test)]"
    )
    compiled = {
        "_Color_A": {
            "display_name": "第三色带",
            "type": "color",
            "default": [1.0, 1.0, 1.0, 0.0],
            "hdr": False,
            "exposed": True,
        }
    }
    color_nodes, properties, _ = convert_node(color, [], compiled, tmp_path, {})
    assert color_nodes[0].output_names == {0: "第三色带"}
    assert properties[0]["default"] == [1.0, 1.0, 1.0, 0.0]

    sampler = parse_node_line(
        "Node;AmplifyShaderEditor.SamplerNode;68;0,0;Inherit;True;Property;"
        "_Tex;纹理;14;1;[HideInInspector];Create;False;0;0;0;True;0;False;-1;"
        "944392c2985544e1887f5223b229458a;944392c2985544e1887f5223b229458a;"
        "True;0;False;white;Auto;False;Object;-1;Auto;Texture2D"
    )
    assert sampler.raw_fields[20] == "-1"
    assert sampler_texture_guid(sampler) == "944392c2985544e1887f5223b229458a"
