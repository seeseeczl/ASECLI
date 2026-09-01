"""REG-0015: graph mutations cannot commit known structural corruption."""

from __future__ import annotations

import json
from pathlib import Path

from asecli.cli.main import app


FIXTURES = Path(__file__).parent / "fixtures"
FUNCTION = FIXTURES / "step-antialiasing.function.txt"


def _copy_fixture(tmp_path: Path, name: str = "graph.shader") -> Path:
    target = tmp_path / name
    target.write_bytes(FUNCTION.read_bytes())
    return target


def test_set_field_rejects_node_id_mutation_without_writing(tmp_path, capsys):
    target = _copy_fixture(tmp_path)
    before = target.read_bytes()

    rc = app(
        [
            "set-field",
            str(target),
            "--node",
            "5",
            "--field",
            "2",
            "--value",
            "500",
            "--write",
        ]
    )
    payload = json.loads(capsys.readouterr().out)

    assert rc == 2
    assert payload["error"]["code"] == "USAGE_ERROR"
    assert target.read_bytes() == before


def test_connect_rejects_second_source_for_same_input(tmp_path, capsys):
    target = _copy_fixture(tmp_path)
    before = target.read_bytes()

    rc = app(["connect", str(target), "--from", "1:0", "--to", "3:0", "--write"])
    payload = json.loads(capsys.readouterr().out)

    assert rc == 2
    assert payload["error"]["code"] == "USAGE_ERROR"
    assert target.read_bytes() == before


def test_validate_duplicate_input_returns_json_failure(tmp_path, capsys):
    target = _copy_fixture(tmp_path)
    text = target.read_text(encoding="utf-8")
    target.write_text(
        text.replace("ASEEND*/", "WireConnection;3;0;1;0\nASEEND*/"),
        encoding="utf-8",
    )

    rc = app(["validate", str(target)])
    payload = json.loads(capsys.readouterr().out)

    assert rc == 2
    assert payload["ok"] is False
    assert payload["error"]["code"] == "VALIDATION_ERROR"
    assert payload["data"]["error_count"] >= 1
    assert any(issue["code"] == "MULTIPLE_INPUT_CONNECTIONS" for issue in payload["data"]["issues"])


def test_add_node_rejects_duplicate_id_without_writing(tmp_path, capsys):
    target = _copy_fixture(tmp_path)
    before = target.read_bytes()
    line = "Node;AmplifyShaderEditor.SaturateNode;5;0,0;Inherit;False;1;0;FLOAT;0;False;1;FLOAT;0"

    rc = app(["add-node", str(target), "--line", line, "--write"])
    payload = json.loads(capsys.readouterr().out)

    assert rc == 2
    assert payload["error"]["code"] == "VALIDATION_ERROR"
    assert target.read_bytes() == before
