"""Output naming and runtime setting fidelity regressions."""
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from asecli.cli.commands import CliError
from asecli.cli.export_sg_command import cmd_export_sg
from asecli.export_sg import ExportError, build_candidate
from tests.test_export_sg import _node, _master, _shader, unity_project


def test_output_suffix_keeps_graph_name_and_receipt_consistent(unity_project):
    value = _node("AmplifyShaderEditor.RangedFloatNode", 10, "-400,0")
    source = unity_project / "Assets/scalar.shader"
    source.write_text(_shader(value, _master(), wires=["WireConnection;1;2;10;0"]))
    args = SimpleNamespace(file=str(source), out_dir=str(source.parent),
                           output_suffix="_20260914_170000")
    result = cmd_export_sg(args)
    spec = json.loads(Path(result["spec_json"]).read_text())
    assert spec["name"] == "Converted/scalar"
    assert Path(result["spec_json"]).name == "scalar_20260914_170000.asecli-to-sgcli.spec.json"
    receipt = json.loads(Path(result["receipt_json"]).read_text())
    for kind in ("spec", "report"):
        path = Path(result[kind + "_json"])
        assert receipt[kind]["path"] == str(path)
        assert receipt[kind]["sha256"] == hashlib.sha256(path.read_bytes()).hexdigest()
    args.output_suffix = "../escape"
    with pytest.raises(CliError) as caught:
        cmd_export_sg(args)
    assert caught.value.code == "USAGE_ERROR"


@pytest.mark.parametrize("label,index", [("  Blend", 9), ("Two Sided", 2),
                                         ("GPU Instancing", 0), ("Tessellation", 1)])
def test_unsupported_shader_settings_remain_blocking(unity_project, label, index):
    master = _master()
    master[master.index(label) + 1] = str(index)
    value = _node("AmplifyShaderEditor.RangedFloatNode", 10, "-400,0")
    source = unity_project / "Assets/settings.shader"
    source.write_text(_shader(value, master, wires=["WireConnection;1;2;10;0"]))
    with pytest.raises(ExportError):
        build_candidate(source, unity_project)
