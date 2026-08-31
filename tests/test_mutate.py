"""REG-0002: mutations produce minimal, correct diffs."""

from pathlib import Path

from asecli.core import AseFile, NodeLine, WireLine

FIXTURES = Path(__file__).parent / "fixtures"


def test_replace_node_minimal_diff():
    text = (FIXTURES / "step-antialiasing.function.txt").read_text(encoding="utf-8")
    f = AseFile.from_text(text)
    node = f.graph.node_by_id("5")
    assert node is not None
    mutated = list(node.raw_fields)
    mutated[-1] = "42"
    f.graph.replace_node(NodeLine(type_name=node.type_name, node_id=node.node_id, raw_fields=mutated))
    out = f.serialize()
    # exactly one line differs
    a = text.splitlines()
    b = out.splitlines()
    assert len(a) == len(b)
    diff = [i for i, (x, y) in enumerate(zip(a, b)) if x != y]
    assert len(diff) == 1


def test_add_node_and_wire():
    text = (FIXTURES / "step-antialiasing.function.txt").read_text(encoding="utf-8")
    f = AseFile.from_text(text)
    before = len(f.graph.instructions)
    f.graph.add_node(NodeLine(type_name="AmplifyShaderEditor.SaturateNode", node_id="99", raw_fields=["Node", "AmplifyShaderEditor.SaturateNode", "99", "-160,0", "Inherit", "False", "1", "0", "FLOAT", "0", "False", "1", "FLOAT", "0"]))
    f.graph.add_wire(WireLine(in_node="6", in_port="0", out_node="99", out_port="0"))
    out = f.serialize()
    f2 = AseFile.from_text(out)
    assert len(f2.graph.instructions) == before + 2
    assert f2.graph.node_by_id("99") is not None
    assert any(w.in_node == "6" and w.in_port == "0" and w.out_node == "99" for w in f2.graph.wires)
