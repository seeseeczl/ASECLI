"""Build the deterministic primary tree used by recursive fishbone layout."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Mapping, Protocol

from .commentary import COMMENTARY_TYPE
from .layout import MASTER_TYPES
from .layout_graph import (
    graph_depths, has_incoming, id_key, immediate_comment_owners, is_master,
    node_position, port_key, reject_cycles,
)
from .local_vars import REGISTER_LOCAL_VAR_TYPE
from .model import AseGraph, WireLine
from .wire_router import WIRE_NODE_TYPE, logical_wires


class Geometry(Protocol):
    width: float
    height: float
    title_height: float
    input_ports: dict[str, tuple[float, float]]
    output_ports: dict[str, tuple[float, float]]


@dataclass
class FishboneTopology:
    ids: set[str]
    types: dict[str, str]
    collapsed_wires: list[WireLine]
    satellites: set[str]
    depths: dict[str, int]
    group_of: dict[str, str]
    current_y: dict[str, float]
    primary_parent: dict[str, str]
    primary_wire: dict[tuple[str, str], WireLine]
    children: dict[str, tuple[str, ...]]
    spine_child: dict[str, str]
    roots: list[str]


def build_fishbone_topology(graph: AseGraph, geometry: Mapping[str, Geometry]) -> FishboneTopology:
    candidates = [
        node for node in graph.nodes
        if node.type_name not in {COMMENTARY_TYPE, WIRE_NODE_TYPE}
    ]
    collapsed = [item.wire for item in logical_wires(graph)]
    connected = {node_id for wire in collapsed for node_id in (wire.out_node, wire.in_node)}
    unavailable = {
        node.node_id for node in candidates
        if node.node_id not in geometry
        or geometry[node.node_id].width <= 0
        or geometry[node.node_id].height <= 0
        or geometry[node.node_id].title_height <= 0
    }
    dormant = {
        node.node_id for node in candidates
        if node.node_id in unavailable and node.type_name in MASTER_TYPES
        and node.node_id not in connected
    }
    missing = sorted(unavailable - dormant, key=id_key)
    if missing:
        raise ValueError(f"editor geometry missing active node(s): {', '.join(missing)}")
    nodes = [node for node in candidates if node.node_id not in dormant]
    ids = {node.node_id for node in nodes}
    types = {node.node_id: node.type_name for node in nodes}
    _require_logical_ports(collapsed, ids, geometry)

    physical: dict[str, list[WireLine]] = defaultdict(list)
    for wire in collapsed:
        if wire.out_node in ids and wire.in_node in ids and wire.out_node != wire.in_node:
            physical[wire.out_node].append(wire)
    satellites = {
        node_id for node_id in ids
        if types[node_id] == REGISTER_LOCAL_VAR_TYPE and not physical.get(node_id)
        and any(wire.in_node == node_id for wire in collapsed)
    }
    outgoing: dict[str, list[WireLine]] = defaultdict(list)
    for source, wires in physical.items():
        outgoing[source].extend(wire for wire in wires if wire.in_node not in satellites)
    reject_cycles(ids, outgoing)
    depths = graph_depths(ids, outgoing)
    group_of = immediate_comment_owners(graph)
    current_y = {node.node_id: node_position(node)[1] for node in nodes}
    primary_parent, primary_wire = _choose_primary(
        ids, outgoing, depths, group_of, current_y,
    )
    children_lists: dict[str, list[str]] = defaultdict(list)
    for child, parent in primary_parent.items():
        children_lists[parent].append(child)
    for parent, members in children_lists.items():
        members.sort(key=lambda child: (
            port_key(primary_wire[(child, parent)].in_port), current_y[child], id_key(child),
        ))
    children = {node_id: tuple(children_lists.get(node_id, [])) for node_id in ids}
    upstream_depth, upstream_size = _measure_topology(ids, children)
    spine_child = _choose_spines(
        children, primary_wire, geometry, upstream_depth, upstream_size, current_y,
    )
    roots = [item for item in ids if item not in primary_parent and item not in satellites]
    roots.sort(key=lambda item: (
        0 if is_master(graph, item) else 1,
        0 if outgoing.get(item) or has_incoming(graph, item) else 1,
        id_key(item),
    ))
    if not roots:
        raise ValueError("meticulous layout found no root node")
    return FishboneTopology(
        ids, types, collapsed, satellites, depths, group_of, current_y,
        primary_parent, primary_wire, children, spine_child, roots,
    )


def _choose_primary(ids, outgoing, depths, group_of, current_y):
    parents, wires = {}, {}
    for source in sorted(ids, key=id_key):
        choices = outgoing.get(source, [])
        if not choices:
            continue
        chosen = min(choices, key=lambda wire: (
            -depths[wire.in_node],
            0 if group_of.get(source) == group_of.get(wire.in_node) else 1,
            port_key(wire.in_port), abs(current_y[source] - current_y[wire.in_node]),
            id_key(wire.in_node),
        ))
        parents[source] = chosen.in_node
        wires[(source, chosen.in_node)] = chosen
    return parents, wires


def _measure_topology(ids, children):
    depths, sizes = {}, {}

    def measure(node_id):
        if node_id in depths:
            return depths[node_id], sizes[node_id]
        branch = children[node_id]
        values = [measure(child) for child in branch]
        depths[node_id] = 0 if not values else 1 + max(item[0] for item in values)
        sizes[node_id] = 1 + sum(item[1] for item in values)
        return depths[node_id], sizes[node_id]

    for node_id in sorted(ids, key=id_key):
        measure(node_id)
    return depths, sizes


def _choose_spines(children, primary_wire, geometry, depths, sizes, current_y):
    result = {}
    for parent, branch in children.items():
        if not branch:
            continue
        if len(branch) >= 3 and len(branch) % 2 == 1:
            result[parent] = branch[len(branch) // 2]
            continue
        candidates = branch[len(branch) // 2 - 1: len(branch) // 2 + 1] if len(branch) >= 4 else branch
        result[parent] = max(candidates, key=lambda child: _spine_score(
            child, parent, primary_wire[(child, parent)], geometry, depths, sizes, current_y,
        ))
    return result


def _spine_score(child, parent, wire, geometry, depths, sizes, current_y):
    label = str((getattr(geometry[parent], "input_port_labels", {}) or {}).get(wire.in_port, "")).lower()
    control = ("strength", "amount", "softness", "saturation", "threshold", "scale")
    data = ("input", "value", "color", "normal", "reflection", "true")
    semantic = -1 if any(word in label for word in control) else int(any(word in label for word in data))
    delta = abs(
        current_y[child] + geometry[child].output_ports[wire.out_port][1]
        - current_y[parent] - geometry[parent].input_ports[wire.in_port][1]
    )
    numeric_port = port_key(wire.in_port)
    port_rank = -float(numeric_port[1]) if numeric_port[0] == 0 else 0.0
    return depths[child], int(sizes[child] > 1), semantic, sizes[child], -delta, port_rank


def _require_logical_ports(wires, ids, geometry):
    for wire in wires:
        if wire.out_node not in ids or wire.in_node not in ids:
            continue
        if wire.out_port not in geometry[wire.out_node].output_ports:
            raise ValueError(f"editor geometry missing output port {wire.out_node}:{wire.out_port}")
        if wire.in_port not in geometry[wire.in_node].input_ports:
            raise ValueError(f"editor geometry missing input port {wire.in_node}:{wire.in_port}")
