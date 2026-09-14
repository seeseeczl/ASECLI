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
def test_precision_unknown_or_mixed_never_folds(precision, white):
    node = _node(f"Out = lerp({white}, C, A);")
    node.settings = {} if precision == "Inherit" else {"precision": precision}
    edges = _edges()
    report = {"diagnostics": [], "mappings": []}
    result = normalize_surface_outputs([node], edges,
        {"surface": "Transparent", "blend": "Multiply"}, {}, report,
        'Pass { Name "Forward"\nBlend DstColor Zero, Zero One\nHLSLPROGRAM\nENDHLSL\n}')
    assert result == ([node], edges)
    assert report["diagnostics"][0]["code"] == "ALPHA_MODULATE_TARGET_CAPABILITY_REQUIRED"
    required = report["diagnostics"][0]["reason"]["required_target_capabilities"]
    assert required["rgb_blend"] == ["DstColor", "Zero"]
    assert required["alpha_blend"] == ["Zero", "One"]
    assert required["implicit_alpha_modulate"] is False
    assert report["surface_semantics"]["rewrites"] == []


def test_native_lerp_mixed_input_precision_is_not_folded():
    nodes, edges, mappings, report = _native_lerp_case()
    nodes[1].settings["precision"] = "Single"
    assert normalize_surface_outputs(nodes, edges,
        {"surface": "Transparent", "blend": "Multiply"}, mappings, report) == (nodes, edges)
    assert any(d["code"] == "ALPHA_MODULATE_TARGET_CAPABILITY_REQUIRED" for d in report["diagnostics"])


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
    with pytest.raises(CliError) as caught:
        cmd_export_sg(SimpleNamespace(file=str(source), out_dir=str(tmp_path / "out"), target_project=None))
    assert caught.value.code == "SG_EXPORT_BLOCKED"
    details = caught.value.data
    assert details["source"]["sha256"] == expected
    blockers = details["blockers"]
    assert [(b["code"], str(b["source_node_id"])) for b in blockers] == [
        ("ALPHA_MODULATE_TARGET_CAPABILITY_REQUIRED", "146")
    ]
    assert details["required_target_capabilities"]["implicit_alpha_modulate"] is False
    assert details["warning_count"] == 16
    assert any(w["code"] == "CUSTOM_INSPECTOR_PRESENTATION_NOT_MIGRATED"
               for w in details["presentation_warnings"])
    assert len(details["custom_function_manifest"]) == 64
    assert not list((tmp_path / "out").glob("*.spec.json"))
    assert not list((tmp_path / "out").glob("*.receipt.json"))
    report = json.loads(Path(details["report_json"]).read_text())
    assert report["source"]["source_recheck_sha256"] == expected
    assert hashlib.sha256(source.read_bytes()).hexdigest() == expected
