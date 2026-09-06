"""REG-0051: meticulous layout governance, comments, and explicit wire routing."""

from pathlib import Path
from types import SimpleNamespace

from asecli.bridge.mcp_client import McpError
from asecli.checks import fix_checksum
from asecli.cli.main import app
from asecli.core import (
    AseFile,
    apply_meticulous_layout,
    govern_comment_purposes,
    meticulous_layout_positions,
    refit_comments_for_layout,
)
from asecli.core.commentary import create_comment_group, inspect_comment_groups
from asecli.core.model import NodeLine, WireLine
from asecli.core.wire_geometry import path_hits_rect
from asecli.core.wire_router import (
    logical_wire_manifest,
    plan_wire_routes,
    routed_wire_paths,
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
            output_ports={
                port: (width, 40.0 + index * 12.0)
                for index, port in enumerate(sorted(outputs[node.node_id]))
            },
        )
    return result


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


def test_comment_purpose_preserves_meaningful_title():
    shader = _graph([("1", "Input")], [])
    group = create_comment_group(shader.graph, ["1"], "计算车漆法线")
    before = shader.graph.node_by_id(group["node_id"]).to_line()
    result = govern_comment_purposes(shader.graph, _geometry(shader.graph), apply=True)
    assert result == [{
        "comment_id": group["node_id"], "status": "existing", "title": "计算车漆法线",
    }]
    assert shader.graph.node_by_id(group["node_id"]).to_line() == before


def test_comment_purpose_infers_unique_register_name():
    shader = _graph([("1", "Input"), ("2", "AmplifyShaderEditor.RegisterLocalVarNode")], [])
    register = shader.graph.node_by_id("2")
    register.raw_fields.extend([
        "Inherit", "False", "CoatMask", "-1", "True", "1", "0",
        "FLOAT", "0", "False", "1", "FLOAT", "0",
    ])
    shader.graph.replace_node(register)
    group = create_comment_group(shader.graph, ["1", "2"], "Comment")
    result = govern_comment_purposes(shader.graph, _geometry(shader.graph), apply=True)
    assert result[0]["status"] == "inferred"
    assert result[0]["suggested_title"] == "生成 CoatMask"
    assert inspect_comment_groups(shader.graph)[0]["title"] == "生成 CoatMask"


def test_comment_purpose_infers_external_consumer_and_port_from_v3_labels():
    shader = _graph([("1", "Input"), ("2", "Consumer")], [("1", "0", "2", "3")])
    group = create_comment_group(shader.graph, ["1"], "Group")
    geometry = _geometry(shader.graph)
    geometry["2"].node_title = "混合清漆"
    geometry["2"].input_port_labels = {"3": "遮罩"}
    result = govern_comment_purposes(shader.graph, geometry, apply=False)
    assert result == [{
        "comment_id": group["node_id"],
        "status": "inferred",
        "title": "Group",
        "suggested_title": "为「混合清漆」计算「遮罩」",
        "source": "external_consumer_port",
    }]
    assert inspect_comment_groups(shader.graph)[0]["title"] == "Group"


def test_comment_purpose_infers_unique_local_sink_and_reports_ambiguous_group():
    shader = _graph(
        [("1", "Input"), ("2", "AmplifyShaderEditor.SaturateNode"), ("3", "Input")],
        [("1", "0", "2", "0")],
    )
    third = shader.graph.node_by_id("3")
    third.raw_fields[3] = "0,400"
    shader.graph.replace_node(third)
    clear = create_comment_group(shader.graph, ["1", "2"], "处理1")
    ambiguous = create_comment_group(shader.graph, ["3"], "临时组2")
    geometry = _geometry(shader.graph)
    geometry["2"].node_title = "限制反射范围"
    geometry["3"].node_title = ""
    result = {
        item["comment_id"]: item
        for item in govern_comment_purposes(shader.graph, geometry, apply=False)
    }
    assert result[clear["node_id"]]["suggested_title"] == "计算「限制反射范围」"
    assert result[ambiguous["node_id"]]["status"] == "unresolved"


def test_comment_refit_separates_unrelated_groups_and_preserves_metadata():
    shader = _graph([("1", "Input"), ("2", "Input")], [])
    second_node = shader.graph.node_by_id("2")
    second_node.raw_fields[3] = "0,400"
    shader.graph.replace_node(second_node)
    create_comment_group(shader.graph, ["1"], "第一组")
    create_comment_group(shader.graph, ["2"], "第二组")
    geometry = _geometry(shader.graph)
    positions = {"1": (0.0, 0.0), "2": (0.0, 0.0)}
    before = {
        item["node_id"]: (tuple(item["members"]), item["color"], item["title"])
        for item in inspect_comment_groups(shader.graph)
    }
    refit_comments_for_layout(shader.graph, geometry, positions)
    groups = sorted(inspect_comment_groups(shader.graph), key=lambda item: item["position"]["y"])
    assert groups[1]["position"]["y"] >= groups[0]["position"]["y"] + groups[0]["height"] + 96
    after = {
        item["node_id"]: (tuple(item["members"]), item["color"], item["title"])
        for item in inspect_comment_groups(shader.graph)
    }
    assert after == before


def test_comment_refit_keeps_nested_group_nested_instead_of_separating_it():
    shader = _graph([("1", "Input"), ("2", "Consumer")], [("1", "0", "2", "0")])
    inner = create_comment_group(shader.graph, ["1"], "内部")
    outer = create_comment_group(shader.graph, [inner["node_id"], "2"], "外部")
    geometry = _geometry(shader.graph)
    positions = {"1": (0.0, 0.0), "2": (250.0, 0.0)}
    refit_comments_for_layout(shader.graph, geometry, positions)
    groups = {item["node_id"]: item for item in inspect_comment_groups(shader.graph)}
    inner_group, outer_group = groups[inner["node_id"]], groups[outer["node_id"]]
    assert outer_group["position"]["x"] <= inner_group["position"]["x"] - 24
    assert outer_group["position"]["y"] <= inner_group["position"]["y"] - 40
    assert outer_group["position"]["x"] + outer_group["width"] >= (
        inner_group["position"]["x"] + inner_group["width"] + 24
    )
    assert outer_group["position"]["y"] + outer_group["height"] >= (
        inner_group["position"]["y"] + inner_group["height"] + 24
    )


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
    assert {item["code"] for item in payload["data"]["audit"]["hard_failures"]} == {
        "COMMENT_WHITESPACE"
    }
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


def test_meticulous_default_preserves_existing_wire_node_position_and_collapses_it():
    shader = _graph(
        [("1", "Input"), ("9", "AmplifyShaderEditor.WireNode"),
         ("100", "AmplifyShaderEditor.TemplateMultiPassMasterNode")],
        [("1", "0", "9", "0"), ("9", "0", "100", "0")],
    )
    anchor = shader.graph.node_by_id("9")
    anchor.raw_fields[3] = "321,654"
    shader.graph.replace_node(anchor)
    geometry = _geometry(shader.graph, widths={"9": 24.0}, heights={"9": 24.0})
    plan = meticulous_layout_positions(shader.graph, geometry)
    assert plan.positions["9"] == (321.0, 654.0)
    assert plan.primary_parent == {"1": "100"}
    assert logical_wire_manifest(shader.graph) == [("1", "0", "100", "0")]
    apply_meticulous_layout(shader.graph, plan)
    assert shader.graph.node_by_id("9").raw_fields[3] == "321,654"


def test_explicit_wire_routing_adds_at_most_two_anchors_when_score_improves():
    shader = _graph(
        [("1", "Input"), ("2", "Obstacle"), ("3", "Consumer")],
        [("1", "0", "3", "0")],
    )
    geometry = _geometry(shader.graph, widths={"1": 100.0, "2": 160.0, "3": 100.0})
    positions = {"1": (0.0, 0.0), "2": (270.0, 0.0), "3": (600.0, 0.0)}
    changes = plan_wire_routes(shader.graph, geometry, positions)
    assert len(changes) == 1
    assert changes[0]["action"] == "add"
    assert len(changes[0]["anchors"]) <= 2
    routed = routed_wire_paths(shader.graph, geometry, positions, changes)
    obstacle = (270.0, 0.0, 430.0, 100.0)
    assert not path_hits_rect(routed[0][1], obstacle)


def test_explicit_wire_routing_does_not_add_anchors_to_clear_horizontal_wire():
    shader = _graph([("1", "Input"), ("3", "Consumer")], [("1", "0", "3", "0")])
    geometry = _geometry(shader.graph, widths={"1": 100.0, "3": 100.0})
    positions = {"1": (0.0, 0.0), "3": (300.0, 0.0)}
    assert plan_wire_routes(shader.graph, geometry, positions) == ()


def test_meticulous_route_write_uses_editor_and_verifies_logical_wire(tmp_path, capsys, monkeypatch):
    shader = _graph(
        [("1", "Input"), ("100", "AmplifyShaderEditor.TemplateMultiPassMasterNode")],
        [("1", "0", "100", "0")],
    )
    project = tmp_path / "Project"
    (project / "Assets").mkdir(parents=True)
    (project / "ProjectSettings").mkdir()
    path = project / "Assets" / "layout.shader"
    path.write_text(shader.serialize(), encoding="utf-8")
    before = path.read_text(encoding="utf-8")
    geometry = _geometry(shader.graph)
    change = ({
        "action": "add",
        "logical_wire": {"from_node": "1", "from_port": "0", "to_node": "100", "to_port": "0"},
        "anchors": [[100.0, -80.0], [200.0, -80.0]],
    },)
    monkeypatch.setattr("asecli.cli.layout_command.inspect_graph_geometry_via_mcp", lambda *a, **k: geometry)
    monkeypatch.setattr("asecli.core.meticulous_layout.plan_wire_routes", lambda *a, **k: change)

    def fake_editor_route(shader_path, changes, **kwargs):
        persisted = AseFile.from_path(shader_path)
        assert persisted.graph.remove_wire("1", "0", "100", "0")
        for node_id, position in (("900", "100,-80"), ("901", "200,-80")):
            persisted.graph.add_node(NodeLine(
                "AmplifyShaderEditor.WireNode", node_id,
                ["Node", "AmplifyShaderEditor.WireNode", node_id, position],
            ))
        persisted.graph.add_wire(WireLine("1", "0", "900", "0"))
        persisted.graph.add_wire(WireLine("900", "0", "901", "0"))
        persisted.graph.add_wire(WireLine("901", "0", "100", "0"))
        path.write_text(fix_checksum(persisted.serialize()), encoding="utf-8")
        return {
            "protocol": "ASECLI_WIRE_ROUTE_V1", "asset_path": "Assets/layout.shader",
            "saved": True, "applied_routes": 1, "created_node_ids": [900, 901],
        }

    monkeypatch.setattr("asecli.cli.layout_command.apply_wire_routes_via_mcp", fake_editor_route)
    assert app(["layout", str(path), "--mode", "meticulous", "--route-wires", "--write"]) == 0
    payload = __import__("json").loads(capsys.readouterr().out)
    assert payload["data"]["wire_route_transaction"]["created_node_ids"] == [900, 901]
    assert logical_wire_manifest(AseFile.from_path(path).graph) == [("1", "0", "100", "0")]
    assert path.with_suffix(".shader.bak").read_text(encoding="utf-8") == before


def test_meticulous_route_failure_restores_original_and_keeps_backup(tmp_path, capsys, monkeypatch):
    shader = _graph(
        [("1", "Input"), ("100", "AmplifyShaderEditor.TemplateMultiPassMasterNode")],
        [("1", "0", "100", "0")],
    )
    project = tmp_path / "Project"
    (project / "Assets").mkdir(parents=True)
    (project / "ProjectSettings").mkdir()
    path = project / "Assets" / "layout.shader"
    path.write_text(shader.serialize(), encoding="utf-8")
    before = path.read_bytes()
    geometry = _geometry(shader.graph)
    change = ({
        "action": "add",
        "logical_wire": {"from_node": "1", "from_port": "0", "to_node": "100", "to_port": "0"},
        "anchors": [[100.0, -80.0]],
    },)
    monkeypatch.setattr("asecli.cli.layout_command.inspect_graph_geometry_via_mcp", lambda *a, **k: geometry)
    monkeypatch.setattr("asecli.core.meticulous_layout.plan_wire_routes", lambda *a, **k: change)
    monkeypatch.setattr(
        "asecli.cli.layout_command.apply_wire_routes_via_mcp",
        lambda *a, **k: (_ for _ in ()).throw(McpError("editor disconnected")),
    )
    assert app(["layout", str(path), "--mode", "meticulous", "--route-wires", "--write"]) == 3
    payload = __import__("json").loads(capsys.readouterr().out)
    assert payload["error"]["code"] == "BRIDGE_ERROR"
    assert payload["data"]["recovery"] == "restored_from_backup"
    assert path.read_bytes() == before
    assert path.with_suffix(".shader.bak").read_bytes() == before
