"""Regression tests for adversarial audit fixes (AA-OPT-001~005)."""

from pathlib import Path

from asecli.core import AseFile
from asecli.checks import fix_checksum, verify_checksum

FIXTURES = Path(__file__).parent / "fixtures"


def _base() -> str:
    return (FIXTURES / "HLIT.shader").read_text(encoding="utf-8")


def test_blank_line_roundtrip_preserved():
    """AA-OPT-002: empty lines inside the graph body must survive roundtrip."""
    text = _base().replace("ASEEND*/", "\nASEEND*/")  # inject blank line before END
    f = AseFile.from_text(text)
    assert f.serialize() == text


def test_crlf_roundtrip_byte_identical():
    """AA-OPT-001: CRLF files must parse and roundtrip byte-identically.

    Converting EOL invalidates the stored checksum (bytes changed) — that is
    correct behavior; fix-checksum must restore validity.
    """
    text = _base().replace("\n", "\r\n")
    f = AseFile.from_text(text)
    assert f.serialize() == text
    ok, _, _ = verify_checksum(f.serialize())
    assert not ok  # expected: original checksum was computed over LF bytes
    from asecli.checks import fix_checksum

    fixed = fix_checksum(f.serialize())
    ok2, _, _ = verify_checksum(fixed)
    assert ok2


def test_crlf_parses_without_error():
    """AA-OPT-001: CRLF must not crash parsing."""
    f = AseFile.from_text(_base().replace("\n", "\r\n"))
    assert len(f.graph.nodes) == 10


def test_create_renames_graph_data(tmp_path, compliant_shader_path):
    """AA-OPT-003: shader name must not remain in node lines after rename."""
    from asecli.cli.main import app

    source = AseFile.from_path(compliant_shader_path)
    source_path = tmp_path / "source.shader"
    source_path.write_text(fix_checksum(source.serialize()), encoding="utf-8")
    out = tmp_path / "renamed.shader"
    rc = app(["create", str(out), "--from", str(source_path), "--name", "BrandNew", "--force"])
    assert rc == 0
    text = out.read_text(encoding="utf-8")
    assert 'Shader "BrandNew"' in text
    assert ";BrandNew;" in text
    assert ";HLIT;" not in text


def test_atomic_write_creates_backup(tmp_path):
    """AA-OPT-004: overwriting an existing file leaves a .bak with old content."""
    from asecli.cli.main import app

    target = tmp_path / "w.shader"
    target.write_text((FIXTURES / "step-antialiasing.function.txt").read_text(encoding="utf-8"), encoding="utf-8")
    rc = app(["set-field", str(target), "--node", "5", "--field", "12", "--value", "77", "--write"])
    assert rc == 0
    bak = target.with_suffix(".shader.bak")
    assert bak.exists()
    assert ";42" not in bak.read_text(encoding="utf-8")
    assert ";77" in target.read_text(encoding="utf-8")


def test_add_node_warns_on_hex_fields(tmp_path, capsys):
    """AA-OPT-005: nodes whose serialized form embeds a 32-hex id produce a warning."""
    import json
    from asecli.cli.main import app

    target = tmp_path / "g.shader"
    target.write_text((FIXTURES / "HLIT.shader").read_text(encoding="utf-8"), encoding="utf-8")
    # TemplateMultiPassMasterNode is opaque; force a runtime node line containing hex via --line
    line = "Node;AmplifyShaderEditor.RelayNode;500;0,0;Inherit;False;94348b07e5e8bab40bd6c8a1e3df54cd;1;0;FLOAT;0;False;1;FLOAT;0"
    rc = app(["add-node", str(target), "--line", line, "--write"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out.strip())
    assert payload["ok"] is True
    assert any("32-hex" in w for w in payload["data"]["warnings"])
