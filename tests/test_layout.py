"""REG-0012: deterministic, safe, meticulous left-to-right layout."""

from asecli.core import AseFile
from asecli.core.layout import layout_positions, tidy

from pathlib import Path

FIXTURES = Path(__file__).parent / "fixtures"


def _build_graph() -> tuple[AseFile, str]:
    text = (FIXTURES / "step-antialiasing.function.txt").read_text(encoding="utf-8")
    f = AseFile.from_text(text)
    # scramble positions to prove layout normalizes them
    for n in f.graph.nodes:
        n.raw_fields[3] = "7777,7777"
        f.graph.replace_node(n)
    return f, f.serialize()


def _build_repeated_branch_graph() -> AseFile:
    return AseFile.from_text(
        """/*ASEBEGIN
Version=19602
Node;AmplifyShaderEditor.FunctionInput;1;7777,7777
Node;AmplifyShaderEditor.FunctionInput;2;7777,7777
Node;AmplifyShaderEditor.SimpleAddOpNode;3;7777,7777
Node;AmplifyShaderEditor.SimpleAddOpNode;4;7777,7777
Node;AmplifyShaderEditor.SaturateNode;5;7777,7777
Node;AmplifyShaderEditor.SaturateNode;6;7777,7777
Node;AmplifyShaderEditor.TemplateMultiPassMasterNode;0;7777,7777
WireConnection;3;0;1;0
WireConnection;4;0;2;0
WireConnection;5;0;3;0
WireConnection;6;0;4;0
WireConnection;0;0;5;0
WireConnection;0;1;6;0
ASEEND*/
"""
    )


def test_layout_moves_only_position_fields():
    f, before = _build_graph()
    moved = tidy(f.graph)
    after = f.serialize()

    a, b = before.splitlines(), after.splitlines()
    assert len(a) == len(b)
    for la, lb in zip(a, b):
        if la.startswith("Node;"):
            fa, fb = la.split(";"), lb.split(";")
            assert fa[:3] == fb[:3]  # marker, type, id unchanged
            assert fa[4:] == fb[4:]  # everything after position unchanged
        else:
            assert la == lb
    assert moved == 7


def test_layout_preserves_wire_set():
    f, _ = _build_graph()
    wires_before = sorted((w.out_node, w.out_port, w.in_node, w.in_port) for w in f.graph.wires)
    tidy(f.graph)
    wires_after = sorted((w.out_node, w.out_port, w.in_node, w.in_port) for w in f.graph.wires)
    assert wires_before == wires_after


def test_layout_deterministic():
    g1, _ = _build_graph()
    g2, _ = _build_graph()
    tidy(g1.graph)
    tidy(g2.graph)
    assert g1.serialize() == g2.serialize()


def test_layout_layers_follow_dataflow():
    text = (FIXTURES / "step-antialiasing.function.txt").read_text(encoding="utf-8")
    f = AseFile.from_text(text)
    pos = layout_positions(f.graph)
    x = {nid: p[0] for nid, p in pos.items()}
    # inputs (1,2) leftmost; subtract(3) next; fwidth(4) and divide(5); saturate(6); output(0) rightmost
    assert x["1"] < x["3"] < x["5"] < x["6"] < x["0"]
    assert x["4"] < x["5"]


def test_master_nodes_forced_last_layer():
    f = AseFile.from_path(FIXTURES / "HLIT.shader")
    pos = layout_positions(f.graph)
    xs = {nid: p[0] for nid, p in pos.items()}
    assert len(set(xs.values())) == 1  # all-masters graph: single aligned column


def test_layout_uses_exact_stage_columns_and_progressive_spacing():
    f = _build_repeated_branch_graph()
    gap_x = 320.0
    pos = layout_positions(f.graph, gap_x=gap_x)

    stages = [("1", "2"), ("3", "4"), ("5", "6"), ("0",)]
    stage_xs = []
    for stage in stages:
        xs = {pos[node_id][0] for node_id in stage}
        assert len(xs) == 1
        stage_xs.append(xs.pop())

    assert [right - left for left, right in zip(stage_xs, stage_xs[1:])] == [gap_x] * 3


def test_repeated_branches_share_the_same_row_rhythm():
    f = _build_repeated_branch_graph()
    gap_y = 140.0
    pos = layout_positions(f.graph, gap_y=gap_y)

    for upper, lower in (("1", "2"), ("3", "4"), ("5", "6")):
        assert abs(pos[upper][1] - pos[lower][1]) == gap_y

    assert pos["1"][1] == pos["3"][1] == pos["5"][1]
    assert pos["2"][1] == pos["4"][1] == pos["6"][1]


def test_every_dag_wire_advances_left_to_right_and_master_is_rightmost():
    f = _build_repeated_branch_graph()
    pos = layout_positions(f.graph)

    for wire in f.graph.wires:
        assert pos[wire.out_node][0] < pos[wire.in_node][0]

    master_x = pos["0"][0]
    assert master_x == max(x for x, _ in pos.values())
    assert all(x < master_x for node_id, (x, _) in pos.items() if node_id != "0")
