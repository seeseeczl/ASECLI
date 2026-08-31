"""REG-0012: layout is deterministic, preserves wires, and only moves x/y."""

import re

from asecli.core import AseFile, NodeLine
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
