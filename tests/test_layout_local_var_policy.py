"""CR-0020: Local Var decisions use distinct consumer groups, not wire count."""

from types import SimpleNamespace

from asecli.core import (
    AseFile,
    apply_meticulous_layout,
    audit_meticulous_layout,
    meticulous_layout_positions,
    refit_comments_for_layout,
)
from asecli.core.commentary import create_comment_group


def _graph(nodes, wires):
    node_lines = "\n".join(f"Node;{type_name};{node_id};0,0" for node_id, type_name in nodes)
    wire_lines = "\n".join(
        f"WireConnection;{target};{in_port};{source};{out_port}"
        for source, out_port, target, in_port in wires
    )
    return AseFile.from_text(f"/*ASEBEGIN\nVersion=19602\n{node_lines}\n{wire_lines}\nASEEND*/\n")


def _geometry(graph):
    inputs = {node.node_id: set() for node in graph.nodes}
    outputs = {node.node_id: set() for node in graph.nodes}
    for wire in graph.wires:
        inputs[wire.in_node].add(wire.in_port)
        outputs[wire.out_node].add(wire.out_port)
    return {
        node.node_id: SimpleNamespace(
            width=180.0,
            height=100.0,
            title_height=24.0,
            input_ports={port: (0.0, 50.0 + index * 12.0) for index, port in enumerate(sorted(inputs[node.node_id]))},
            output_ports={port: (180.0, 40.0 + index * 12.0) for index, port in enumerate(sorted(outputs[node.node_id]))},
        )
        for node in graph.nodes
    }


def _set_positions(shader, positions):
    for node_id, position in positions.items():
        node = shader.graph.node_by_id(node_id)
        node.raw_fields[3] = position
        shader.graph.replace_node(node)


def _audit(shader):
    geometry = _geometry(shader.graph)
    plan = meticulous_layout_positions(shader.graph, geometry)
    apply_meticulous_layout(shader.graph, plan)
    refit_comments_for_layout(shader.graph, geometry, plan.positions)
    return plan, audit_meticulous_layout(shader.graph, geometry, plan, moved=len(plan.positions))


def test_repeated_direct_use_inside_one_group_is_allowed():
    shader = _graph(
        [("1", "Producer"), ("2", "Consumer"), ("3", "Consumer"), ("4", "Consumer"),
         ("100", "AmplifyShaderEditor.TemplateMultiPassMasterNode")],
        [("1", "0", "2", "0"), ("1", "0", "3", "0"), ("1", "0", "4", "0"),
         ("2", "0", "100", "0"), ("3", "0", "100", "1"), ("4", "0", "100", "2")],
    )
    _set_positions(shader, {"1": "0,0", "2": "0,0", "3": "0,160", "4": "0,320"})
    create_comment_group(shader.graph, ["1", "2", "3", "4"], "同组算法")
    _, report = _audit(shader)
    assert report["remote_direct_wires"] == []


def test_two_consumer_groups_require_local_var_for_external_direct_wire():
    shader = _graph(
        [("1", "Producer"), ("2", "Consumer"), ("3", "Consumer"),
         ("100", "AmplifyShaderEditor.TemplateMultiPassMasterNode")],
        [("1", "0", "2", "0"), ("1", "0", "3", "0"),
         ("2", "0", "100", "0"), ("3", "0", "100", "1")],
    )
    _set_positions(shader, {"1": "0,0", "2": "300,0", "3": "300,500"})
    local = create_comment_group(shader.graph, ["1", "2"], "生产与本地消费")
    remote = create_comment_group(shader.graph, ["3"], "远端消费")
    plan, report = _audit(shader)
    assert report["remote_direct_wires"] == [{
        "from": "1", "to": "3", "stage_span": plan.depths["1"] - plan.depths["3"],
        "producer_group": local["node_id"], "consumer_group": remote["node_id"],
        "consumer_groups": sorted([local["node_id"], remote["node_id"]]),
        "reason": "consumed_by_multiple_groups",
    }]
