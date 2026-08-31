"""REG-0001: parse -> serialize must be byte-identical on real samples."""

from pathlib import Path

from asecli.core import AseFile, parse_graph_text

FIXTURES = Path(__file__).parent / "fixtures"


def test_shader_roundtrip_byte_identical():
    text = (FIXTURES / "HLIT.shader").read_text(encoding="utf-8")
    f = AseFile.from_text(text)
    assert f.serialize() == text


def test_shader_parses_expected_nodes():
    f = AseFile.from_path(FIXTURES / "HLIT.shader")
    assert f.graph.version == "19109"
    assert len(f.graph.nodes) == 10
    assert all(n.type_name == "AmplifyShaderEditor.TemplateMultiPassMasterNode" for n in f.graph.nodes)


def test_function_asset_roundtrip():
    text = (FIXTURES / "step-antialiasing.function.txt").read_text(encoding="utf-8")
    f = AseFile.from_text(text)
    assert f.serialize() == text
    assert len(f.graph.nodes) == 7
    assert len(f.graph.wires) == 7
