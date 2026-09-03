"""REG-0024: native ASE CommentaryNode semantic grouping."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

from asecli.checks import fix_checksum, verify_checksum
from asecli.checks import validate_file
from asecli.core import (
    AseFile,
    comment_containment_issues,
    create_comment_group,
    inspect_comment_groups,
    parse_graph_text,
    refit_comment_groups,
)


ROOT = Path(__file__).parents[1]
SRC = str(ROOT / "src")


def sample_shader() -> str:
    return fix_checksum('''Shader "Tests/Comments"
{
    Properties {}
    SubShader {}
}
/*ASEBEGIN
Version=19602
Node;AmplifyShaderEditor.ColorNode;1;100,200;Inherit;False;Constant
Node;AmplifyShaderEditor.RangedFloatNode;2;500,260;Inherit;False;Constant
Node;AmplifyShaderEditor.SimpleAddOpNode;3;900,100;Inherit;False
ASEEND*/
//CHKSM=PLACEHOLDER''')


def run_cli(*args: str) -> tuple[int, dict]:
    env = dict(os.environ)
    env["PYTHONPATH"] = SRC
    proc = subprocess.run(
        [sys.executable, "-m", "asecli.cli.main", *args], capture_output=True, text=True, env=env
    )
    assert len(proc.stdout.splitlines()) == 1, (proc.stdout, proc.stderr)
    return proc.returncode, json.loads(proc.stdout)


def test_create_comment_group_calculates_native_bounds_without_moving_members():
    shader = AseFile.from_text(sample_shader())
    before = {node.node_id: node.to_line() for node in shader.graph.nodes}
    group = create_comment_group(shader.graph, ["1", "2"], "明度越高，强度越小")
    assert group == {
        "node_id": "4",
        "position": {"x": 50.0, "y": 150.0},
        "width": 700.0,
        "height": 280.0,
        "note": "Comment",
        "members": ["1", "2"],
        "title": "明度越高，强度越小",
        "color": "1,1,1,1",
    }
    assert {node.node_id: node.to_line() for node in shader.graph.nodes if node.node_id in before} == before
    assert shader.graph.wires == []


def test_reads_real_ase_19602_commentary_line():
    graph = parse_graph_text("""Version=19602
Node;AmplifyShaderEditor.CommentaryNode;1069;-5680.915,4572.911;Inherit;False;670.7803;297.4448;;2;1212;1218;明度越高，强度越小;1,1,1,1;0;0
""")
    group = inspect_comment_groups(graph)[0]
    assert group["members"] == ["1212", "1218"]
    assert group["note"] == ""
    assert group["title"] == "明度越高，强度越小"


def test_nested_comment_group_contains_inner_frame_not_its_children():
    shader = AseFile.from_text(sample_shader())
    inner = create_comment_group(shader.graph, ["1", "2"], "明度越高，强度越小", note="")
    outer = create_comment_group(shader.graph, [inner["node_id"], "3"], "控制不同颜色明度下的不同灯光强度")
    assert outer["members"] == ["4", "3"]
    assert outer["position"] == {"x": 0.0, "y": 50.0}
    assert outer["width"] == 1150.0
    assert outer["height"] == 430.0
    assert [group["title"] for group in inspect_comment_groups(shader.graph)] == [
        "明度越高，强度越小", "控制不同颜色明度下的不同灯光强度"
    ]
    assert comment_containment_issues(shader.graph, {}) == []


def test_rejects_unrelated_comment_group_overlap_but_allows_touching_edges():
    shader = AseFile.from_text(sample_shader())
    create_comment_group(shader.graph, ["1"], "左组", padding=50)
    with pytest.raises(ValueError, match="overlap unrelated comment group"):
        create_comment_group(shader.graph, ["2"], "重叠组", padding=200)

    touching = AseFile.from_text(sample_shader())
    create_comment_group(touching.graph, ["1"], "左组", padding=50)
    group = create_comment_group(touching.graph, ["2"], "右组", padding=150)
    assert group["position"]["x"] == 350.0
    assert comment_containment_issues(touching.graph, {}) == []


def test_bounds_check_reports_existing_unrelated_comment_overlap():
    shader = AseFile.from_text(sample_shader())
    create_comment_group(shader.graph, ["1"], "左组", padding=50)
    right = create_comment_group(shader.graph, ["2"], "右组", padding=50)
    right_node = shader.graph.node_by_id(right["node_id"])
    assert right_node is not None
    right_node.raw_fields[3] = "300,210"
    shader.graph.replace_node(right_node)

    issues = comment_containment_issues(shader.graph, {})
    overlap = next(issue for issue in issues if issue["code"] == "COMMENT_GROUP_OVERLAP")
    assert overlap["comment_ids"] == ["4", "5"]
    assert overlap["overlap"] == {"x": 300.0, "y": 210.0, "width": 50.0, "height": 160.0}


def test_cli_comment_group_dry_run_then_write_backup_checksum_and_query(tmp_path):
    path = tmp_path / "comments.shader"
    original = sample_shader()
    path.write_text(original, encoding="utf-8")
    before = hashlib.sha256(path.read_bytes()).hexdigest()
    args = ("comment-group", str(path), "--nodes", "1,2", "--title", "颜色关联")
    code, payload = run_cli(*args)
    assert code == 0 and payload["data"]["written"] is False
    assert payload["data"]["structural_validation"] == "passed"
    assert payload["data"]["visual_validation"] == "pending"
    assert hashlib.sha256(path.read_bytes()).hexdigest() == before
    assert not path.with_suffix(".shader.bak").exists()

    code, payload = run_cli(*args, "--write")
    assert code == 0 and payload["data"]["written"] is True
    assert path.with_suffix(".shader.bak").read_text(encoding="utf-8") == original
    assert verify_checksum(path.read_text(encoding="utf-8"))[0] is True
    assert AseFile.from_path(path).serialize() == path.read_text(encoding="utf-8")
    code, payload = run_cli("comment-group", str(path))
    assert code == 0 and payload["data"]["groups"][0]["title"] == "颜色关联"
    assert payload["data"]["structural_validation"] == "passed"
    assert payload["data"]["visual_validation"] == "pending"
    code, payload = run_cli("validate", str(path))
    assert code == 0 and payload["data"]["error_count"] == 0


@pytest.mark.parametrize(
    "extra,error_code",
    [
        (("--nodes", "1,1", "--title", "重复"), "COMMENT_GROUP_ERROR"),
        (("--nodes", "99", "--title", "缺失"), "NOT_FOUND"),
        (("--nodes", "1", "--title", "坏;标题"), "COMMENT_GROUP_ERROR"),
        (("--nodes", "1", "--title", "坏\n标题"), "COMMENT_GROUP_ERROR"),
        (("--nodes", "1"), "USAGE_ERROR"),
    ],
)
def test_cli_comment_group_failures_are_atomic_single_json(tmp_path, extra, error_code):
    path = tmp_path / "invalid.shader"
    original = sample_shader()
    path.write_text(original, encoding="utf-8")
    code, payload = run_cli("comment-group", str(path), *extra, "--write")
    assert code == 2 and payload["error"]["code"] == error_code
    assert path.read_text(encoding="utf-8") == original
    assert not path.with_suffix(".shader.bak").exists()


def test_cli_rejects_creation_options_without_nodes(tmp_path):
    path = tmp_path / "usage.shader"
    path.write_text(sample_shader(), encoding="utf-8")
    code, payload = run_cli("comment-group", str(path), "--padding", "30")
    assert code == 2 and payload["error"]["code"] == "USAGE_ERROR"


def test_rejects_regrouping_child_or_selecting_nested_frame_and_child():
    shader = AseFile.from_text(sample_shader())
    inner = create_comment_group(shader.graph, ["1", "2"], "内层")
    with pytest.raises(ValueError, match="already belongs"):
        create_comment_group(shader.graph, ["1", "3"], "错误外层")
    with pytest.raises(ValueError, match="not both"):
        create_comment_group(shader.graph, [inner["node_id"], "2"], "错误嵌套")


def test_validate_reports_dangling_and_malformed_comment_membership():
    dangling = AseFile.from_text(sample_shader().replace(
        "ASEEND*/",
        "Node;AmplifyShaderEditor.CommentaryNode;4;0,0;Inherit;False;300;200;Comment;1;99;缺失;1,1,1,1;0;0\nASEEND*/",
    ))
    assert "DANGLING_COMMENT_MEMBER" in {issue["code"] for issue in validate_file(dangling)}
    malformed = AseFile.from_text(sample_shader().replace(
        "ASEEND*/",
        "Node;AmplifyShaderEditor.CommentaryNode;4;0,0;Inherit;False;300;200;Comment;2;1;坏;1,1,1,1;0;0\nASEEND*/",
    ))
    assert "MALFORMED_COMMENT" in {issue["code"] for issue in validate_file(malformed)}


def test_live_bounds_detect_and_refit_member_outside_frame_without_moving_nodes():
    shader = AseFile.from_text(sample_shader())
    create_comment_group(shader.graph, ["1", "2"], "运行时尺寸", padding=30)
    before_nodes = {
        node.node_id: node.raw_fields[3]
        for node in shader.graph.nodes
        if node.node_id in {"1", "2"}
    }
    live_bounds = {
        "1": (100.0, 200.0, 460.0, 120.0),
        "2": (500.0, 260.0, 256.0, 63.0),
    }
    issues = comment_containment_issues(shader.graph, live_bounds)
    assert issues[0]["code"] == "COMMENT_MEMBER_OUTSIDE_FRAME"
    assert issues[0]["overflow"]["right"] == 26.0

    changes = refit_comment_groups(shader.graph, live_bounds, padding=30)
    assert len(changes) == 1
    assert comment_containment_issues(shader.graph, live_bounds) == []
    assert {
        node.node_id: node.raw_fields[3]
        for node in shader.graph.nodes
        if node.node_id in {"1", "2"}
    } == before_nodes
    fitted = inspect_comment_groups(shader.graph)[0]
    assert fitted["position"] == {"x": 70.0, "y": 170.0}
    assert fitted["width"] == 716.0
    assert fitted["height"] == 183.0
