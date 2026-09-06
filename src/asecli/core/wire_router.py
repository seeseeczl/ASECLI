"""Explicit, topology-preserving routing plans for ASE WireNode anchors."""

from __future__ import annotations

from dataclasses import dataclass
from math import hypot
from typing import Mapping, Protocol

from .model import AseGraph, WireLine
from .wire_geometry import path_hits_rect, paths_cross

WIRE_NODE_TYPE = "AmplifyShaderEditor.WireNode"
ROUTE_CLEARANCE = 48.0


class Geometry(Protocol):
    width: float
    height: float
    input_ports: dict[str, tuple[float, float]]
    output_ports: dict[str, tuple[float, float]]


@dataclass(frozen=True)
class LogicalWire:
    wire: WireLine
    wire_nodes: tuple[str, ...]


def logical_wires(graph: AseGraph) -> list[LogicalWire]:
    """Collapse each WireNode chain into its original logical connection."""
    types = {node.node_id: node.type_name for node in graph.nodes}
    wire_ids = {node_id for node_id, type_name in types.items() if type_name == WIRE_NODE_TYPE}
    outgoing: dict[str, list[WireLine]] = {}
    for wire in graph.wires:
        outgoing.setdefault(wire.out_node, []).append(wire)

    result: list[LogicalWire] = []

    def follow(first: WireLine, current: WireLine, anchors: tuple[str, ...], visiting: set[str]) -> None:
        if current.in_node not in wire_ids:
            result.append(LogicalWire(
                WireLine(first.out_node, first.out_port, current.in_node, current.in_port),
                anchors,
            ))
            return
        anchor = current.in_node
        if anchor in visiting:
            raise ValueError(f"WireNode routing cycle at node {anchor}")
        next_wires = outgoing.get(anchor, [])
        if len(next_wires) != 1:
            raise ValueError(f"WireNode {anchor} must have exactly one outgoing connection")
        follow(first, next_wires[0], anchors + (anchor,), visiting | {anchor})

    for wire in graph.wires:
        if wire.out_node not in wire_ids:
            follow(wire, wire, (), set())
    return sorted(result, key=lambda item: _wire_key(item.wire))


def plan_wire_routes(
    graph: AseGraph,
    geometry: Mapping[str, Geometry],
    positions: dict[str, tuple[float, float]],
) -> tuple[dict, ...]:
    """Move existing anchors first, then propose at most two for a direct wire."""
    routes = logical_wires(graph)
    rects = {
        node_id: (x, y, x + geometry[node_id].width, y + geometry[node_id].height)
        for node_id, (x, y) in positions.items()
        if node_id in geometry and graph.node_by_id(node_id).type_name != WIRE_NODE_TYPE
    }
    route_points = {
        _wire_key(route.wire): [_wire_node_anchor(node_id, geometry, positions) for node_id in route.wire_nodes]
        for route in routes
    }
    changes: list[dict] = []
    for route in routes:
        key = _wire_key(route.wire)
        baseline = route_points[key]
        baseline_score = _route_score(route, baseline, routes, route_points, geometry, positions, rects)
        if baseline_score[:2] == (0, 0):
            continue
        anchor_count = len(route.wire_nodes) or 2
        candidates = _candidate_points(route.wire, anchor_count, geometry, positions, rects)
        best_points, best_score = baseline, baseline_score
        for candidate in candidates:
            score = _route_score(route, candidate, routes, route_points, geometry, positions, rects)
            if score < best_score:
                best_points, best_score = candidate, score
        # Routing may not trade a new collision/crossing for a shorter path.
        if (
            best_points == baseline
            or best_score[0] > baseline_score[0]
            or best_score[1] > baseline_score[1]
            or best_score[:2] == baseline_score[:2]
        ):
            continue
        route_points[key] = best_points
        logical = {
            "from_node": route.wire.out_node, "from_port": route.wire.out_port,
            "to_node": route.wire.in_node, "to_port": route.wire.in_port,
        }
        if route.wire_nodes:
            moved = []
            for node_id, point in zip(route.wire_nodes, best_points):
                old = positions[node_id]
                new = _wire_node_position(node_id, point, geometry, positions)
                if new != old:
                    positions[node_id] = new
                    moved.append({"wire_node_id": node_id, "from": list(old), "to": list(new)})
            if moved:
                changes.append({"action": "move", "logical_wire": logical, "anchors": moved})
        else:
            changes.append({
                "action": "add", "logical_wire": logical,
                "anchors": [[round(x, 1), round(y, 1)] for x, y in best_points],
            })
    return tuple(changes)


def routed_wire_paths(
    graph: AseGraph,
    geometry: Mapping[str, Geometry],
    positions: Mapping[str, tuple[float, float]],
    route_changes: tuple[dict, ...] = (),
) -> list[tuple[WireLine, list[tuple[float, float]]]]:
    additions = {
        _dict_wire_key(change["logical_wire"]): [tuple(point) for point in change["anchors"]]
        for change in route_changes if change["action"] == "add"
    }
    result = []
    for route in logical_wires(graph):
        wire = route.wire
        points = additions.get(
            _wire_key(wire),
            [_wire_node_anchor(node_id, geometry, positions) for node_id in route.wire_nodes],
        )
        result.append((wire, _sample_route(wire, points, geometry, positions)))
    return result


def logical_wire_manifest(graph: AseGraph) -> list[tuple[str, str, str, str]]:
    return sorted(
        (item.wire.out_node, item.wire.out_port, item.wire.in_node, item.wire.in_port)
        for item in logical_wires(graph)
    )


def _route_score(route, points, routes, route_points, geometry, positions, rects):
    path = _sample_route(route.wire, points, geometry, positions)
    hits = sum(
        path_hits_rect(path, rect)
        for node_id, rect in rects.items()
        if node_id not in {route.wire.out_node, route.wire.in_node}
    )
    crossings = 0
    endpoints = {route.wire.out_node, route.wire.in_node}
    for other in routes:
        if other is route or endpoints & {other.wire.out_node, other.wire.in_node}:
            continue
        other_path = _sample_route(
            other.wire, route_points[_wire_key(other.wire)], geometry, positions,
        )
        crossings += paths_cross(path, other_path)
    length = sum(hypot(b[0] - a[0], b[1] - a[1]) for a, b in zip(path, path[1:]))
    return hits, crossings, round(length, 3)


def _candidate_points(wire, count, geometry, positions, rects):
    source = _port_anchor(wire.out_node, wire.out_port, True, geometry, positions)
    target = _port_anchor(wire.in_node, wire.in_port, False, geometry, positions)
    between = [
        rect for node_id, rect in rects.items()
        if node_id not in {wire.out_node, wire.in_node}
        and not (rect[2] < min(source[0], target[0]) or rect[0] > max(source[0], target[0]))
    ]
    tops = [min(source[1], target[1]) - ROUTE_CLEARANCE]
    bottoms = [max(source[1], target[1]) + ROUTE_CLEARANCE]
    if between:
        tops.append(min(rect[1] for rect in between) - ROUTE_CLEARANCE)
        bottoms.append(max(rect[3] for rect in between) + ROUTE_CLEARANCE)
    channels = sorted(set(tops + bottoms + [(source[1] + target[1]) * 0.5]))
    values = []
    for channel_y in channels:
        if count == 1:
            values.append([(round((source[0] + target[0]) * 0.5, 1), round(channel_y, 1))])
        else:
            left_x = source[0] + (target[0] - source[0]) / 3.0
            right_x = source[0] + 2.0 * (target[0] - source[0]) / 3.0
            points = []
            for index in range(count):
                fraction = index / max(1, count - 1)
                points.append((round(left_x + (right_x - left_x) * fraction, 1), round(channel_y, 1)))
            values.append(points)
    return values


def _sample_route(wire, anchors, geometry, positions, samples=12):
    points = [
        _port_anchor(wire.out_node, wire.out_port, True, geometry, positions),
        *anchors,
        _port_anchor(wire.in_node, wire.in_port, False, geometry, positions),
    ]
    result = []
    for index, (start, end) in enumerate(zip(points, points[1:])):
        span = max(24.0, abs(end[0] - start[0]) * 0.5)
        control_a, control_b = (start[0] + span, start[1]), (end[0] - span, end[1])
        segment = [_bezier(start, control_a, control_b, end, step / samples) for step in range(samples + 1)]
        result.extend(segment if index == 0 else segment[1:])
    return result


def _port_anchor(node_id, port_id, output, geometry, positions):
    offsets = geometry[node_id].output_ports if output else geometry[node_id].input_ports
    x, y = positions[node_id]
    dx, dy = offsets[port_id]
    return x + dx, y + dy


def _wire_node_anchor(node_id, geometry, positions):
    x, y = positions[node_id]
    measured = geometry.get(node_id)
    if measured is None:
        return x, y
    return x + measured.width * 0.5, y + measured.height * 0.5


def _wire_node_position(node_id, point, geometry, positions):
    measured = geometry.get(node_id)
    if measured is None:
        return round(point[0], 1), round(point[1], 1)
    return round(point[0] - measured.width * 0.5, 1), round(point[1] - measured.height * 0.5, 1)


def _bezier(p0, p1, p2, p3, t):
    one = 1.0 - t
    return (
        one ** 3 * p0[0] + 3 * one * one * t * p1[0] + 3 * one * t * t * p2[0] + t ** 3 * p3[0],
        one ** 3 * p0[1] + 3 * one * one * t * p1[1] + 3 * one * t * t * p2[1] + t ** 3 * p3[1],
    )


def _wire_key(wire):
    return f"{wire.out_node}:{wire.out_port}->{wire.in_node}:{wire.in_port}"


def _dict_wire_key(value):
    return f"{value['from_node']}:{value['from_port']}->{value['to_node']}:{value['to_port']}"
