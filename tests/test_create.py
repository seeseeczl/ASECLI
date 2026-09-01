"""REG-0014: create keeps the template shell and replaces only the ASE graph."""

from __future__ import annotations

from pathlib import Path

from asecli.cli.main import app
from asecli.core import AseFile


FIXTURES = Path(__file__).parent / "fixtures"
SHADER = FIXTURES / "HLIT.shader"
FUNCTION = FIXTURES / "step-antialiasing.function.txt"


def test_create_graph_from_keeps_one_shader_shell(tmp_path):
    out = tmp_path / "graph-from.shader"

    rc = app(["create", str(out), "--from", str(SHADER), "--graph-from", str(SHADER)])

    assert rc == 0
    text = out.read_text(encoding="utf-8")
    assert text.count('Shader "') == 1
    assert text.count("/*ASEBEGIN") == 1
    assert text.count("ASEEND*/") == 1
    created = AseFile.from_text(text)
    donor = AseFile.from_path(SHADER)
    assert [node.to_line() for node in created.graph.nodes] == [node.to_line() for node in donor.graph.nodes]


def test_create_graph_from_function_does_not_inject_yaml_shell(tmp_path):
    out = tmp_path / "function-graph.shader"

    rc = app(["create", str(out), "--from", str(SHADER), "--graph-from", str(FUNCTION)])

    assert rc == 0
    text = out.read_text(encoding="utf-8")
    assert "m_functionInfo:" not in text
    assert len(AseFile.from_text(text).graph.nodes) == 7


def test_create_renames_after_donor_graph_injection(tmp_path):
    out = tmp_path / "renamed-graph.shader"

    rc = app(
        [
            "create",
            str(out),
            "--from",
            str(SHADER),
            "--graph-from",
            str(SHADER),
            "--name",
            "BrandNew",
        ]
    )

    assert rc == 0
    text = out.read_text(encoding="utf-8")
    assert text.count('Shader "BrandNew"') == 1
    assert ";BrandNew;" in text
    assert ";HLIT;" not in text
