"""REG-0012: deterministic, safe, meticulous left-to-right layout."""

from types import SimpleNamespace

import pytest

from asecli.core import AseFile
from asecli.core import (
    apply_meticulous_layout,
    audit_meticulous_layout,
    meticulous_layout_positions,
    refit_comments_for_layout,
)
from asecli.core.commentary import create_comment_group, inspect_comment_groups
from asecli.core.layout import layout_positions, tidy
from asecli.cli.main import app

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


def _graph(nodes: list[tuple[str, str]], wires: list[tuple[str, str, str, str]]) -> AseFile:
    node_lines = "\n".join(f"Node;{type_name};{node_id};0,0" for node_id, type_name in nodes)
    wire_lines = "\n".join(
        f"WireConnection;{target};{in_port};{source};{out_port}"
        for source, out_port, target, in_port in wires
    )
    return AseFile.from_text(f"/*ASEBEGIN\nVersion=19602\n{node_lines}\n{wire_lines}\nASEEND*/\n")


def _geometry(graph, *, heights=None, widths=None):
    heights = heights or {}
    widths = widths or {}
    inputs = {node.node_id: set() for node in graph.nodes}
    outputs = {node.node_id: set() for node in graph.nodes}
    for wire in graph.wires:
        inputs[wire.in_node].add(wire.in_port)
        outputs[wire.out_node].add(wire.out_port)
    result = {}
    for node in graph.nodes:
        port_count = len(inputs[node.node_id])
        default_height = max(100.0, 60.0 + max(0, port_count - 1) * 12.0)
        width, height = widths.get(node.node_id, 180.0), heights.get(node.node_id, default_height)
        input_offsets = {
            port: (0.0, height / 2.0 + (index - (port_count - 1) / 2.0) * 12.0)
            for index, port in enumerate(sorted(inputs[node.node_id]))
        }
        result[node.node_id] = SimpleNamespace(
            width=width,
            height=height,
            title_height=24.0,
            input_ports=input_offsets,
            output_ports={port: (width, 40.0 + index * 12.0) for index, port in enumerate(sorted(outputs[node.node_id]))},
        )
    return result


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


def test_layout_cli_separates_structural_and_visual_validation(tmp_path, capsys):
    path = tmp_path / "layout.shader"
    path.write_text(
        (FIXTURES / "step-antialiasing.function.txt").read_text(encoding="utf-8"),
        encoding="utf-8",
    )

    assert app(["layout", str(path)]) == 0
    payload = __import__("json").loads(capsys.readouterr().out)
    assert payload["data"]["structural_validation"] == "passed"
    assert payload["data"]["visual_validation"] == "pending"


def test_meticulous_centers_one_two_five_and_ten_input_branches():
    for count in (1, 2, 5, 10):
        nodes = [(str(index), "AmplifyShaderEditor.FunctionInput") for index in range(1, count + 1)]
        nodes.append(("100", "AmplifyShaderEditor.TemplateMultiPassMasterNode"))
        wires = [(str(index), "0", "100", str(index - 1)) for index in range(1, count + 1)]
        shader = _graph(nodes, wires)
        geometry = _geometry(shader.graph)
        plan = meticulous_layout_positions(shader.graph, geometry)
        children = plan.children["100"]
        centers = [plan.positions[item][1] + geometry[item].height / 2 for item in children]
        assert centers == sorted(centers)
        child_center = (plan.subtree_bounds[children[0]][1] + plan.subtree_bounds[children[-1]][3]) / 2
        parent_center = plan.positions["100"][1] + geometry["100"].height / 2
        assert abs(parent_center - child_center) <= 0.1


def test_meticulous_recursively_centers_uneven_third_level_subtrees():
    shader = _graph(
        [("1", "Input"), ("2", "Input"), ("3", "Input"), ("10", "Branch"),
         ("11", "Branch"), ("100", "AmplifyShaderEditor.TemplateMultiPassMasterNode")],
        [("1", "0", "10", "0"), ("2", "0", "10", "1"), ("3", "0", "11", "0"),
         ("10", "0", "100", "0"), ("11", "0", "100", "1")],
    )
    geometry = _geometry(shader.graph, heights={"2": 180.0, "11": 140.0})
    plan = meticulous_layout_positions(shader.graph, geometry)
    for parent in ("10", "100"):
        branch = plan.children[parent]
        top = min(plan.subtree_bounds[item][1] for item in branch)
        bottom = max(plan.subtree_bounds[item][3] for item in branch)
        center = plan.positions[parent][1] + geometry[parent].height / 2
        assert abs(center - (top + bottom) / 2) <= 0.1
    assert not _overlap(plan.subtree_bounds["10"], plan.subtree_bounds["11"])


def test_meticulous_aligns_children_to_input_port_span_not_body_center():
    shader = _graph(
        [("1", "Input"), ("2", "Input"), ("100", "AmplifyShaderEditor.TemplateMultiPassMasterNode")],
        [("1", "0", "100", "0"), ("2", "0", "100", "1")],
    )
    geometry = _geometry(shader.graph, heights={"100": 240.0})
    geometry["100"].input_ports.update({"0": (0.0, 40.0), "1": (0.0, 80.0)})
    plan = meticulous_layout_positions(shader.graph, geometry)
    child_center = (plan.subtree_bounds["1"][1] + plan.subtree_bounds["2"][3]) / 2.0
    port_center = plan.positions["100"][1] + 60.0
    body_center = plan.positions["100"][1] + 120.0
    assert abs(child_center - port_center) <= 0.1
    assert child_center != body_center


def test_meticulous_rejects_data_flow_cycles():
    shader = _graph(
        [("1", "Node"), ("2", "Node")],
        [("1", "0", "2", "0"), ("2", "0", "1", "0")],
    )
    with pytest.raises(ValueError, match="data-flow cycle"):
        meticulous_layout_positions(shader.graph, _geometry(shader.graph))


def test_meticulous_shared_source_has_one_primary_parent_and_remains_left_of_all_consumers():
    shader = _graph(
        [("1", "Input"), ("10", "Consumer"), ("11", "Consumer"),
         ("100", "AmplifyShaderEditor.TemplateMultiPassMasterNode")],
        [("1", "0", "10", "0"), ("1", "0", "11", "0"),
         ("10", "0", "100", "0"), ("11", "0", "100", "1")],
    )
    geometry = _geometry(shader.graph)
    plan = meticulous_layout_positions(shader.graph, geometry)
    assert plan.primary_parent["1"] in {"10", "11"}
    assert len(plan.secondary_edges) == 1
    assert plan.positions["1"][0] < plan.positions["10"][0]
    assert plan.positions["1"][0] < plan.positions["11"][0]


def test_meticulous_local_var_endpoints_stay_near_producer_and_consumer():
    shader = _graph(
        [("1", "Producer"), ("2", "AmplifyShaderEditor.RegisterLocalVarNode"),
         ("3", "AmplifyShaderEditor.GetLocalVarNode"), ("4", "Consumer"),
         ("100", "AmplifyShaderEditor.TemplateMultiPassMasterNode")],
        [("1", "0", "2", "0"), ("3", "0", "4", "0"), ("4", "0", "100", "0")],
    )
    geometry = _geometry(shader.graph)
    plan = meticulous_layout_positions(shader.graph, geometry)
    register_gap = plan.positions["2"][0] - (plan.positions["1"][0] + geometry["1"].width)
    get_gap = plan.positions["4"][0] - (plan.positions["3"][0] + geometry["3"].width)
    assert 64 <= register_gap <= 160
    assert 64 <= get_gap <= 160


def test_meticulous_refits_nested_comments_inside_out():
    shader = _graph(
        [("1", "Input"), ("2", "Consumer"), ("100", "AmplifyShaderEditor.TemplateMultiPassMasterNode")],
        [("1", "0", "2", "0"), ("2", "0", "100", "0")],
    )
    inner = create_comment_group(shader.graph, ["1", "2"], "内部")
    outer = create_comment_group(shader.graph, [inner["node_id"], "100"], "外部")
    geometry = _geometry(shader.graph)
    plan = meticulous_layout_positions(shader.graph, geometry)
    apply_meticulous_layout(shader.graph, plan)
    changes = refit_comments_for_layout(shader.graph, geometry, plan.positions)
    groups = {item["node_id"]: item for item in inspect_comment_groups(shader.graph)}
    assert {item["comment_id"] for item in changes} == {inner["node_id"], outer["node_id"]}
    assert groups[outer["node_id"]]["position"]["x"] < groups[inner["node_id"]]["position"]["x"]
    report = audit_meticulous_layout(shader.graph, geometry, plan, moved=3)
    assert report["comment_containment"] == []
    assert report["comment_overlap"] == []


def test_meticulous_is_idempotent_after_first_application():
    shader = _build_repeated_branch_graph()
    geometry = _geometry(shader.graph)
    first = meticulous_layout_positions(shader.graph, geometry)
    apply_meticulous_layout(shader.graph, first)
    second = meticulous_layout_positions(shader.graph, geometry)
    assert second.positions == first.positions
    assert apply_meticulous_layout(shader.graph, second) == 0


def test_meticulous_repeated_subtrees_share_one_internal_template():
    shader = _build_repeated_branch_graph()
    geometry = _geometry(shader.graph)
    plan = meticulous_layout_positions(shader.graph, geometry)
    apply_meticulous_layout(shader.graph, plan)
    report = audit_meticulous_layout(shader.graph, geometry, plan, moved=7)
    assert report["repeated_module_mismatches"] == []


def test_meticulous_cli_emits_v2_audit_without_writing(tmp_path, capsys, monkeypatch):
    shader = _graph(
        [("1", "Input"), ("100", "AmplifyShaderEditor.TemplateMultiPassMasterNode")],
        [("1", "0", "100", "0")],
    )
    path = tmp_path / "layout.shader"
    path.write_text(shader.serialize(), encoding="utf-8")
    geometry = _geometry(shader.graph)
    monkeypatch.setattr("asecli.cli.layout_command.inspect_graph_geometry_via_mcp", lambda *a, **k: geometry)
    before = path.read_bytes()
    assert app(["layout", str(path), "--mode", "meticulous", "--audit"]) == 0
    payload = __import__("json").loads(capsys.readouterr().out)
    assert payload["data"]["audit"]["schema"] == "asecli.graph-layout.v2"
    assert payload["data"]["written"] is False
    assert path.read_bytes() == before


def test_meticulous_write_is_atomic_and_recomputes_checksum(tmp_path, capsys, monkeypatch):
    shader = _graph(
        [("1", "Input"), ("100", "AmplifyShaderEditor.TemplateMultiPassMasterNode")],
        [("1", "0", "100", "0")],
    )
    path = tmp_path / "layout.shader"
    path.write_text(shader.serialize(), encoding="utf-8")
    geometry = _geometry(shader.graph)
    monkeypatch.setattr("asecli.cli.layout_command.inspect_graph_geometry_via_mcp", lambda *a, **k: geometry)
    before = path.read_text(encoding="utf-8")
    assert app(["layout", str(path), "--mode", "meticulous", "--write"]) == 0
    payload = __import__("json").loads(capsys.readouterr().out)
    assert payload["data"]["written"] is True
    assert payload["data"]["checksum_recomputed"] is True
    assert path.with_suffix(".shader.bak").read_text(encoding="utf-8") == before
    assert path.read_text(encoding="utf-8") != before


def test_meticulous_hard_gate_refuses_write_and_preserves_file(tmp_path, capsys, monkeypatch):
    shader = _graph(
        [("1", "Input"), ("100", "AmplifyShaderEditor.TemplateMultiPassMasterNode")],
        [("1", "0", "100", "0")],
    )
    create_comment_group(shader.graph, ["1"], "过空单节点框")
    path = tmp_path / "layout.shader"
    path.write_text(shader.serialize(), encoding="utf-8")
    geometry = _geometry(shader.graph, heights={"1": 20.0}, widths={"1": 20.0})
    monkeypatch.setattr("asecli.cli.layout_command.inspect_graph_geometry_via_mcp", lambda *a, **k: geometry)
    before = path.read_bytes()
    assert app(["layout", str(path), "--mode", "meticulous", "--write"]) == 2
    payload = __import__("json").loads(capsys.readouterr().out)
    assert payload["error"]["code"] == "LAYOUT_ERROR"
    assert {item["code"] for item in payload["data"]["audit"]["hard_failures"]} == {"COMMENT_WHITESPACE"}
    assert path.read_bytes() == before
    assert not path.with_suffix(".shader.bak").exists()


def test_meticulous_requires_every_connected_port(tmp_path, capsys, monkeypatch):
    shader = _graph(
        [("1", "Input"), ("100", "AmplifyShaderEditor.TemplateMultiPassMasterNode")],
        [("1", "0", "100", "0")],
    )
    path = tmp_path / "layout.shader"
    path.write_text(shader.serialize(), encoding="utf-8")
    geometry = _geometry(shader.graph)
    geometry["100"].input_ports.clear()
    monkeypatch.setattr("asecli.cli.layout_command.inspect_graph_geometry_via_mcp", lambda *a, **k: geometry)
    assert app(["layout", str(path), "--mode", "meticulous", "--audit"]) == 2
    payload = __import__("json").loads(capsys.readouterr().out)
    assert payload["error"]["code"] == "LAYOUT_ERROR"
    assert "missing input port 100:0" in payload["error"]["message"]


def test_meticulous_audit_and_write_are_mutually_exclusive(tmp_path, capsys):
    path = tmp_path / "layout.shader"
    path.write_text(_build_repeated_branch_graph().serialize(), encoding="utf-8")
    assert app(["layout", str(path), "--mode", "meticulous", "--audit", "--write"]) == 2
    payload = __import__("json").loads(capsys.readouterr().out)
    assert payload["error"]["code"] == "USAGE_ERROR"


def _overlap(left, right):
    return not (left[2] <= right[0] or right[2] <= left[0] or left[3] <= right[1] or right[3] <= left[1])
