"""Precision, bounded Remap and complete agent diagnostics regressions."""

import hashlib
import json
import os
from pathlib import Path
from types import SimpleNamespace

import pytest

from asecli.cli.commands import CliError
from asecli.cli.export_sg_command import cmd_export_sg
from asecli.sg_export.model import SemanticEdge, SemanticNode
from asecli.sg_export.surface_semantics import normalize_surface_outputs
from tests.test_surface_semantics import _node, _edges, _native_lerp_case
from tests.test_export_sg import _node as ase_node, _master, _shader


@pytest.mark.parametrize("location", ["compiled", "graph"])
def test_custom_editor_diagnostics(tmp_path, location):
    (tmp_path / "Assets").mkdir()
    (tmp_path / "ProjectSettings").mkdir()
    value = ase_node('AmplifyShaderEditor.RangedFloatNode', 10, '-400,0')
    master = _master()
    if location == "graph": master[9] = "Unknown.MaterialMutator"
    shader = _shader(value, master, wires=['WireConnection;1;2;10;0'])
    if location == "compiled":
        shader = shader.replace('/*ASEBEGIN', 'CustomEditor "Unknown.MaterialMutator"\n/*ASEBEGIN')
    source = tmp_path / 'Assets/GUI.shader'
    source.write_text(shader)
    with pytest.raises(CliError) as caught:
        cmd_export_sg(SimpleNamespace(file=str(source), out_dir=str(tmp_path / 'out')))
    details = caught.value.data
    assert caught.value.code == "SG_EXPORT_BLOCKED"
    assert details['spec_written'] is False and details['receipt_written'] is False
    assert details['retry_unchanged_input'] is False
    assert details['blocker_count'] == len(details['blockers'])
    assert any(item['classification'] == 'custom_shader_gui' and
               item['material_side_effects'] == 'unproven' and
               'Unknown.MaterialMutator' in item['details'] for item in details['blockers'])


@pytest.mark.parametrize("precision,white", [
    ("Single", "float3(1,1,1)"), ("Inherit", "half3(1,1,1)"),
    ("Half", "float3(1,1,1)"), ("Half", "(1.0).xxx"),
])
def test_precision_unknown_or_mixed_folds_with_warning(precision, white):
    node = _node(f"Out = lerp({white}, C, A);")
    node.settings = {} if precision == "Inherit" else {"precision": precision}
    edges = _edges()
    report = {"diagnostics": [], "mappings": []}
    result = normalize_surface_outputs([node], edges,
        {"surface": "Transparent", "blend": "Multiply"}, {}, report,
        'Pass { Name "Forward"\nBlend DstColor Zero, Zero One\nHLSLPROGRAM\nENDHLSL\n}')
    assert result[0] == []
    assert SemanticEdge("color", 0, "SurfaceDescription.BaseColor", 0) in result[1]
    assert report["diagnostics"] == []
    proof = report["precision_warnings"][0]["evidence"]
    assert proof["source_node_precision"] == precision
    assert proof["target_precision"] == "Half"
    assert proof["bitwise_equivalence"] == "not_proven"
    assert "source_effective_precision" not in proof
    assert "unresolved" not in report["surface_semantics"]
    assert report["surface_semantics"]["rewrites"][0]["target_modulation_count"] == 1


def test_native_lerp_mixed_input_precision_folds_with_warning():
    nodes, edges, mappings, report = _native_lerp_case()
    nodes[1].settings["precision"] = "Single"
    result = normalize_surface_outputs(nodes, edges,
        {"surface": "Transparent", "blend": "Multiply"}, mappings, report,
        'Pass { Name "Forward"\nBlend DstColor Zero, Zero One\nHLSLPROGRAM\nENDHLSL\n}')
    assert result != (nodes, edges)
    assert report["diagnostics"] == []
    assert report["precision_warnings"][0]["evidence"]["source_operand_precisions"]


@pytest.mark.parametrize("graph,warning", [("Single", True), ("Half", False)])
def test_graph_inheritance_is_recorded_without_changing_node(graph, warning):
    node = _node()
    node.settings = {"precision": "Inherit"}
    report = {"diagnostics": [], "mappings": [], "source_graph_precision": graph}
    normalize_surface_outputs([node], _edges(),
        {"surface": "Transparent", "blend": "Multiply"}, {}, report,
        'Pass { Name "Forward"\nBlend DstColor Zero, Zero One\nHLSLPROGRAM\nENDHLSL\n}')
    assert node.settings == {"precision": "Inherit"}
    assert bool(report.get("precision_warnings")) is warning
    assert report["surface_semantics"]["fold_precision"]["source_resolved_precision"] == graph


def _remap():
    return {"source": "String", "body": "Out = V2.x + (V0 - V1.x) * (V2.y - V2.x) / (V1.y - V1.x);",
            "ports": [{"name": name, "type": kind, "direction": direction}
                      for name, kind, direction in [("Out", "Vector1", "Output"),
                          ("V0", "Vector1", "Input"), ("V1", "Vector2", "Input"), ("V2", "Vector2", "Input")]]}


def test_upstream_custom_function_is_preserved_and_does_not_block_terminal_fold():
    terminal = _node()
    upstream = SemanticNode("57", "ase_57", "custom-function", [0, 0],
                            output_names={0: "Out"}, function=_remap(),
                            settings={"precision": "Single"})
    edges = [SemanticEdge("ase_57", 0, terminal.target_id, -1),
             SemanticEdge("alpha", 0, terminal.target_id, -2),
             SemanticEdge(terminal.target_id, 0, "SurfaceDescription.BaseColor", 0),
             SemanticEdge("alpha", 0, "SurfaceDescription.Alpha", 0)]
    mappings = {"146": {0: (terminal.target_id, 0)}, "57": {0: (upstream.target_id, 0)}}
    report = {"diagnostics": [], "mappings": []}
    nodes, result_edges = normalize_surface_outputs(
        [upstream, terminal], edges, {"surface": "Transparent", "blend": "Multiply"},
        mappings, report,
        'Pass { Name "Forward"\nBlend DstColor Zero, Zero One\nHLSLPROGRAM\nENDHLSL\n}')
    assert nodes == [upstream]
    assert SemanticEdge("ase_57", 0, "SurfaceDescription.BaseColor", 0) in result_edges
    assert report["diagnostics"] == []


@pytest.mark.skipif(not os.environ.get("ASECLI_WAVE_NOISE_SOURCE"), reason="private real sample opt-in")
def test_pinned_real_wave_noise(tmp_path):
    source = Path(os.environ["ASECLI_WAVE_NOISE_SOURCE"])
    expected = "36cf3579f71d8e8bc2a7b7c79de5ff0b4b55713b8660e5310fa231a28c30719b"
    assert hashlib.sha256(source.read_bytes()).hexdigest() == expected
    result = cmd_export_sg(SimpleNamespace(file=str(source), out_dir=str(tmp_path / "out"),
                                          target_project=None, output_suffix="_20260914_170000"))
    assert result["written"]
    assert len(result["precision_warnings"]) == 1
    spec = json.loads(Path(result["spec_json"]).read_text())
    report = json.loads(Path(result["report_json"]).read_text())
    assert spec["graph_settings"]["precision"] == "Single"
    assert spec["target"]["blend"] == "Multiply"
    semantics = result["surface_semantics"]
    assert semantics["source_pass_blend"] == semantics["target_pass_blend"]
    assert semantics["rewrites"][0]["source_modulation_count"] == 1
    assert semantics["rewrites"][0]["target_modulation_count"] == 1
    assert not any(n["id"] == "ase_146" for n in spec["nodes"])
    assert all(c["status"] == "verified" for c in report["checks"].values())
    assert "precision_difference_or_unknown" in report["checks"]["blend_equation"]["evidence"]
    assert report["evidence"]["render_compared"] == "not_run"
    assert report["evidence"]["consumer_loaded"] == "not_run"
    assert report["source"]["source_recheck_sha256"] == expected
    assert hashlib.sha256(source.read_bytes()).hexdigest() == expected
    assert Path(result["receipt_json"]).is_file()
    by_id = {node["id"]: node for node in spec["nodes"]}
    manifest = result["custom_function_manifest"]
    assert len(manifest) == 64
    for entry in manifest:
        if entry["source_node_id"] == "146":
            assert entry["mapping"] == "folded_into_target_pipeline"
            continue
        function = by_id[entry["target_node_id"]]["function"]
        raw = json.dumps(function, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
        assert hashlib.sha256(raw).hexdigest() == entry["function_sha256"]
