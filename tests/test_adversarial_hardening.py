"""AA-OPT-009~016 adversarial regression matrix."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from asecli.bridge.recompile import RECOMPILE_SNIPPET
from asecli.checks import ChecksumFormatError, fix_checksum, validate_file, verify_checksum
from asecli.cli.io import UnsafeWritePathError, WriteConflictError, atomic_write
from asecli.cli.main import app
from asecli.core import (
    AseFile,
    create_comment_group,
    inspect_comment_groups,
    layout_positions,
    remove_node,
    set_node_field,
    tidy,
)


FIXTURES = Path(__file__).parent / "fixtures"
SHADER = FIXTURES / "HLIT.shader"


def _local_var_shader(*, target: str = "1", get_name: str = "Value", get_type: str = "FLOAT", cycle=False):
    wire = "WireConnection;1;0;2;0\n" if cycle else ""
    return fix_checksum(
        'Shader "Tests/LocalVars"\n{\n}\n/*ASEBEGIN\n'
        "Version=19602\n"
        "Node;AmplifyShaderEditor.RegisterLocalVarNode;1;0,0;Inherit;False;Value;-1;True;1;0;FLOAT;0;False;1;FLOAT;0\n"
        f"Node;AmplifyShaderEditor.GetLocalVarNode;2;500,0;Inherit;False;{target};{get_name};1;0;OBJECT;;False;1;{get_type};0\n"
        f"{wire}ASEEND*/\n//CHKSM=PLACEHOLDER"
    )


def test_secure_write_rejects_legacy_tmp_symlink_without_touching_victim(tmp_path):
    target = tmp_path / "target.shader"
    victim = tmp_path / "victim.txt"
    victim.write_text("ORIGINAL", encoding="utf-8")
    target.with_suffix(".shader.tmp").symlink_to(victim)

    with pytest.raises(UnsafeWritePathError, match="legacy temporary"):
        atomic_write(target, "MUTATED", expected_digest=None)

    assert victim.read_text(encoding="utf-8") == "ORIGINAL"
    assert not target.exists()


def test_secure_write_rejects_backup_symlink_without_touching_victim(tmp_path):
    target = tmp_path / "target.shader"
    target.write_text("BEFORE", encoding="utf-8")
    victim = tmp_path / "victim.txt"
    victim.write_text("ORIGINAL", encoding="utf-8")
    target.with_suffix(".shader.bak").symlink_to(victim)

    from asecli.cli.io import file_digest

    with pytest.raises(UnsafeWritePathError, match="backup symlink"):
        atomic_write(target, "AFTER", expected_digest=file_digest(target))

    assert target.read_text(encoding="utf-8") == "BEFORE"
    assert victim.read_text(encoding="utf-8") == "ORIGINAL"


def test_stale_snapshot_is_rejected_instead_of_losing_first_update(tmp_path):
    target = tmp_path / "race.shader"
    target.write_bytes(SHADER.read_bytes())
    writer_a = AseFile.from_path(target)
    writer_b = AseFile.from_path(target)
    set_node_field(writer_a.graph, "0", 3, "111,222")
    set_node_field(writer_b.graph, "1", 3, "333,444")

    atomic_write(target, writer_a.serialize(), expected_digest=writer_a.source_digest)
    with pytest.raises(WriteConflictError):
        atomic_write(target, writer_b.serialize(), expected_digest=writer_b.source_digest)

    final = AseFile.from_path(target)
    assert final.graph.node_by_id("0").raw_fields[3] == "111,222"
    assert final.graph.node_by_id("1").raw_fields[3] == "0,0"


def test_checksum_uses_only_terminal_standalone_trailer():
    original = SHADER.read_text(encoding="utf-8")
    adversarial = original.replace("{", "{\n    // decoy //CHKSM=NOT_THE_TRAILER", 1)
    fixed = fix_checksum(adversarial)

    assert "ASEBEGIN" in fixed
    assert len(fixed) > 100_000
    assert verify_checksum(fixed)[0] is True


def test_checksum_rejects_multiple_standalone_markers():
    original = SHADER.read_text(encoding="utf-8")
    adversarial = original.replace("{", "{\n//CHKSM=DECOY", 1)
    with pytest.raises(ChecksumFormatError, match="multiple"):
        fix_checksum(adversarial)


def test_local_var_validation_covers_missing_target_name_type_and_cycle():
    dangling = validate_file(AseFile.from_text(_local_var_shader(target="999")))
    wrong_target = validate_file(AseFile.from_text(_local_var_shader(target="2")))
    wrong_name = validate_file(AseFile.from_text(_local_var_shader(get_name="Other")))
    wrong_type = validate_file(AseFile.from_text(_local_var_shader(get_type="FLOAT3")))
    cycle = validate_file(AseFile.from_text(_local_var_shader(cycle=True)))

    assert "DANGLING_LOCAL_VAR" in {item["code"] for item in dangling}
    assert "INVALID_LOCAL_VAR_TARGET" in {item["code"] for item in wrong_target}
    assert "LOCAL_VAR_NAME_MISMATCH" in {item["code"] for item in wrong_name}
    assert "LOCAL_VAR_TYPE_MISMATCH" in {item["code"] for item in wrong_type}
    assert "LOCAL_VAR_REFERENCE_CYCLE" in {item["code"] for item in cycle}


def test_referenced_register_cannot_be_removed():
    graph = AseFile.from_text(_local_var_shader()).graph
    with pytest.raises(ValueError, match="referenced by Get nodes: 2"):
        remove_node(graph, "1")
    assert graph.node_by_id("1") is not None


def test_layout_uses_local_var_semantic_edge():
    graph = AseFile.from_text(_local_var_shader()).graph
    positions = layout_positions(graph)
    assert positions["1"][0] < positions["2"][0]


def test_layout_keeps_nested_commentary_as_fixed_composite():
    graph = AseFile.from_text(_local_var_shader()).graph
    inner = create_comment_group(graph, ["1"], "注册变量")
    create_comment_group(graph, [inner["node_id"], "2"], "局部变量算法")
    frozen_ids = {group["node_id"] for group in inspect_comment_groups(graph)} | {"1", "2"}
    before = {node.node_id: node.raw_fields[3] for node in graph.nodes if node.node_id in frozen_ids}

    assert tidy(graph) == 0
    after = {node.node_id: node.raw_fields[3] for node in graph.nodes if node.node_id in frozen_ids}
    assert after == before


def test_mixed_eol_roundtrip_is_byte_identical_from_text_and_path(tmp_path):
    original = SHADER.read_bytes().decode("utf-8")
    mixed = original.replace("Version=19109\n", "Version=19109\r\n", 1)
    assert AseFile.from_text(mixed).serialize() == mixed

    target = tmp_path / "mixed.shader"
    target.write_bytes(mixed.encode("utf-8"))
    assert AseFile.from_path(target).serialize().encode("utf-8") == target.read_bytes()


def test_create_rejects_name_injection_and_preserves_same_named_comment(
    tmp_path, capsys, compliant_shader_path
):
    template = tmp_path / "template.shader"
    source = AseFile.from_path(compliant_shader_path)
    create_comment_group(source.graph, ["1"], "HLIT", note="unrelated help text")
    template.write_text(fix_checksum(source.serialize()), encoding="utf-8", newline="")

    injected = tmp_path / "injected.shader"
    rc = app(["create", str(injected), "--from", str(template), "--name", 'Bad"\nShader "Nested'])
    payload = json.loads(capsys.readouterr().out)
    assert rc == 2 and payload["error"]["code"] == "USAGE_ERROR"
    assert not injected.exists()

    output = tmp_path / "renamed.shader"
    assert app(["create", str(output), "--from", str(template), "--name", "BrandNew"]) == 0
    capsys.readouterr()
    created = AseFile.from_path(output)
    assert inspect_comment_groups(created.graph)[0]["title"] == "HLIT"
    assert created.graph.node_by_id("1").raw_fields[12] == "BrandNew"
    assert verify_checksum(output.read_text(encoding="utf-8"))[0] is True


def test_recompile_snippet_restores_window_in_finally():
    assert "var previousWindow = AmplifyShaderEditor.UIUtils.CurrentWindow;" in RECOMPILE_SNIPPET
    assert "try" in RECOMPILE_SNIPPET and "finally" in RECOMPILE_SNIPPET
    finally_block = RECOMPILE_SNIPPET.split("finally", 1)[1]
    assert "AmplifyShaderEditor.UIUtils.CurrentWindow = previousWindow;" in finally_block
    assert "UnityEditor.Selection.activeObject = previousSelection;" in finally_block
    assert "win.Close()" in finally_block
