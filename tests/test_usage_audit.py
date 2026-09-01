"""Graph audit distinguishes output-dead nodes from external consumers."""

from __future__ import annotations

import json
from pathlib import Path

from asecli.checks import fix_checksum, usage_audit
from asecli.cli.main import app
from asecli.core import AseFile


def _project(tmp_path: Path) -> Path:
    root = tmp_path / "Project"
    (root / "Assets").mkdir(parents=True)
    (root / "ProjectSettings").mkdir()
    shader = root / "Assets" / "Usage.shader"
    shader.write_text(
        fix_checksum('''Shader "Tests/Usage" {}
/*ASEBEGIN
Version=19602
Node;AmplifyShaderEditor.RangedFloatNode;1;0,0;Inherit;False;Property;_Live;Live
Node;AmplifyShaderEditor.RangedFloatNode;2;0,100;Inherit;False;Property;_External;External
Node;AmplifyShaderEditor.RangedFloatNode;3;0,200;Inherit;False;Constant
Node;AmplifyShaderEditor.TemplateMultiPassMasterNode;4;300,0;Inherit;False;True
WireConnection;4;0;1;0
ASEEND*/
//CHKSM=PLACEHOLDER'''),
        encoding="utf-8",
    )
    (root / "Assets" / "UsageShaderGUI.cs").write_text(
        'class UsageShaderGUI { const string Key = "_External"; }\n',
        encoding="utf-8",
    )
    return shader


def test_usage_audit_preserves_external_property_and_reports_real_candidate(tmp_path):
    shader = _project(tmp_path)
    result = usage_audit(str(shader), AseFile.from_path(shader).graph)
    assert [item["node_id"] for item in result["unused_candidates"]] == ["3"]
    assert [item["node_id"] for item in result["external_consumers"]] == ["2"]
    assert result["external_consumers"][0]["external_references"] == [
        {"path": "Assets/UsageShaderGUI.cs", "line": 1}
    ]


def test_remove_node_refuses_external_property_without_explicit_override(tmp_path, capsys):
    shader = _project(tmp_path)
    rc = app(["remove-node", str(shader), "--node", "2", "--write"])
    payload = json.loads(capsys.readouterr().out)
    assert rc == 2
    assert payload["error"]["code"] == "EXTERNAL_REFERENCE"
    assert AseFile.from_path(shader).graph.node_by_id("2") is not None
