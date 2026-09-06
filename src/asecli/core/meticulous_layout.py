"""Mind-map-style, editor-geometry-aware layout for ASE DAGs."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Mapping, Protocol

from .commentary import COMMENTARY_TYPE
from .layout import MASTER_TYPES, apply_positions
from .layout_graph import (
    alignment_offset, descendants, graph_depths, has_incoming, id_key,
    immediate_comment_owners, is_master, node_position, node_rect,
    overlaps_with_gap, port_key, reject_cycles, require_connected_ports,
    round_coord, sibling_gap,
)
from .local_vars import GET_LOCAL_VAR_TYPE, REGISTER_LOCAL_VAR_TYPE
from .model import AseGraph, WireLine

HORIZONTAL_GAP = 96.0
SIBLING_GAP = 32.0
MODULE_GAP = 96.0


class Geometry(Protocol):
    width: float
    height: float
    title_height: float
    input_ports: dict[str, tuple[float, float]]
    output_ports: dict[str, tuple[float, float]]


@dataclass(frozen=True)
class MeticulousLayoutPlan:
    positions: dict[str, tuple[float, float]]
    primary_parent: dict[str, str]
    children: dict[str, tuple[str, ...]]
    roots: tuple[str, ...]
    depths: dict[str, int]
    subtree_bounds: dict[str, tuple[float, float, float, float]]
    secondary_edges: tuple[tuple[str, str, str, str], ...]


def meticulous_layout_positions(
    graph: AseGraph,
    geometry: Mapping[str, Geometry],
) -> MeticulousLayoutPlan:
    """Lay out upstream branches recursively around their consumer's center."""
    candidates = [node for node in graph.nodes if node.type_name != COMMENTARY_TYPE]
    connected = {
        node_id for wire in graph.wires
        for node_id in (wire.out_node, wire.in_node)
    }
    unavailable = {
        node.node_id for node in candidates
        if node.node_id not in geometry
        or geometry[node.node_id].width <= 0
        or geometry[node.node_id].height <= 0
        or geometry[node.node_id].title_height <= 0
    }
    dormant_masters = {
        node.node_id for node in candidates
        if node.node_id in unavailable
        and node.type_name in MASTER_TYPES
        and node.node_id not in connected
    }
    missing_active = sorted(unavailable - dormant_masters, key=id_key)
    if missing_active:
        raise ValueError(f"editor geometry missing active node(s): {', '.join(missing_active)}")
    nodes = [node for node in candidates if node.node_id not in dormant_masters]
    ids = {node.node_id for node in nodes}
    types = {node.node_id: node.type_name for node in nodes}
    missing = sorted(ids - set(geometry), key=id_key)
    if missing:
        raise ValueError(f"editor geometry missing node(s): {', '.join(missing)}")
    require_connected_ports(graph, geometry, ids)
    physical_outgoing: dict[str, list[WireLine]] = defaultdict(list)
    for wire in graph.wires:
        if wire.out_node in ids and wire.in_node in ids and wire.out_node != wire.in_node:
            physical_outgoing[wire.out_node].append(wire)
    satellites = {
        node_id for node_id in ids
        if types[node_id] == REGISTER_LOCAL_VAR_TYPE and not physical_outgoing.get(node_id)
        and any(wire.in_node == node_id for wire in graph.wires)
    }
    outgoing: dict[str, list[WireLine]] = defaultdict(list)
    for source, wires in physical_outgoing.items():
        outgoing[source].extend(wire for wire in wires if wire.in_node not in satellites)
    reject_cycles(ids, outgoing)

    depths = graph_depths(ids, outgoing)
    group_of = immediate_comment_owners(graph)
    current_y = {node.node_id: node_position(node)[1] for node in nodes}
    primary_parent: dict[str, str] = {}
    primary_wire: dict[tuple[str, str], WireLine] = {}
    for source in sorted(ids, key=id_key):
        candidates = outgoing.get(source, [])
        if not candidates:
            continue
        chosen = min(candidates, key=lambda wire: (
            -depths[wire.in_node],
            0 if group_of.get(source) == group_of.get(wire.in_node) else 1,
            abs(current_y[source] - current_y[wire.in_node]),
            port_key(wire.in_port), id_key(wire.in_node),
        ))
        primary_parent[source] = chosen.in_node
        primary_wire[(source, chosen.in_node)] = chosen

    children_lists: dict[str, list[str]] = defaultdict(list)
    for child, parent in primary_parent.items():
        children_lists[parent].append(child)
    for parent, members in children_lists.items():
        members.sort(key=lambda child: (
            port_key(primary_wire[(child, parent)].in_port), current_y[child], id_key(child),
        ))
    children = {node_id: tuple(children_lists.get(node_id, [])) for node_id in ids}
    subtree_height: dict[str, float] = {}
    subtree_above: dict[str, float] = {}
    def measure(node_id: str) -> float:
        if node_id in subtree_height:
            return subtree_height[node_id]
        branch = children[node_id]
        alignment = alignment_offset(node_id, branch, primary_wire, geometry)
        above, below = alignment, geometry[node_id].height - alignment
        if branch:
            child_height = sum(measure(child) for child in branch)
            child_height += sum(
                sibling_gap(left, right, group_of, SIBLING_GAP, MODULE_GAP)
                for left, right in zip(branch, branch[1:])
            )
            above, below = max(above, child_height / 2.0), max(below, child_height / 2.0)
        value = above + below
        subtree_above[node_id] = above
        subtree_height[node_id] = value
        return value

    roots = [node_id for node_id in ids if node_id not in primary_parent and node_id not in satellites]
    roots.sort(key=lambda node_id: (
        0 if is_master(graph, node_id) else 1,
        0 if outgoing.get(node_id) or has_incoming(graph, node_id) else 1,
        id_key(node_id),
    ))
    if not roots:
        raise ValueError("meticulous layout found no root node")
    for root in roots:
        measure(root)

    width_by_depth: dict[int, float] = defaultdict(float)
    for node_id in ids:
        width_by_depth[depths[node_id]] = max(width_by_depth[depths[node_id]], geometry[node_id].width)
    main = roots[0]
    anchor_x, anchor_y = node_position(graph.node_by_id(main))
    column_x = {0: anchor_x}
    for depth in range(1, max(depths.values(), default=0) + 1):
        column_x[depth] = column_x[depth - 1] - HORIZONTAL_GAP - width_by_depth[depth]

    positions: dict[str, tuple[float, float]] = {}
    subtree_bounds: dict[str, tuple[float, float, float, float]] = {}
    def place(node_id: str, alignment_y: float) -> None:
        if types[node_id] == GET_LOCAL_VAR_TYPE and node_id in primary_parent:
            consumer_x = positions[primary_parent[node_id]][0]
            x = consumer_x - HORIZONTAL_GAP - geometry[node_id].width
        else:
            x = column_x[depths[node_id]]
        branch = children[node_id]
        y = alignment_y - alignment_offset(node_id, branch, primary_wire, geometry)
        positions[node_id] = (round_coord(x), round_coord(y))
        if branch:
            combined = sum(subtree_height[child] for child in branch)
            combined += sum(sibling_gap(a, b, group_of, SIBLING_GAP, MODULE_GAP) for a, b in zip(branch, branch[1:]))
            cursor = alignment_y - combined / 2.0
            for index, child in enumerate(branch):
                place(child, cursor + subtree_above[child])
                cursor += subtree_height[child]
                if index + 1 < len(branch):
                    cursor += sibling_gap(child, branch[index + 1], group_of, SIBLING_GAP, MODULE_GAP)
        members = descendants(node_id, children)
        rects = [node_rect(item, positions, geometry) for item in members]
        subtree_bounds[node_id] = (
            min(rect[0] for rect in rects), min(rect[1] for rect in rects),
            max(rect[2] for rect in rects), max(rect[3] for rect in rects),
        )

    main_alignment = anchor_y + alignment_offset(main, children[main], primary_wire, geometry)
    place(main, main_alignment)
    cursor = subtree_bounds[main][3] + MODULE_GAP
    root_bundles: dict[tuple[str, str], list[str]] = defaultdict(list)
    for root in roots[1:]:
        owner = group_of.get(root)
        root_bundles[("comment", owner) if owner else ("node", root)].append(root)
    bundles = sorted(
        root_bundles.values(),
        key=lambda bundle: (min(current_y[item] for item in bundle), min(id_key(item) for item in bundle)),
    )
    ordered_roots = [main]
    for bundle in bundles:
        bundle.sort(key=lambda item: (
            0 if outgoing.get(item) or has_incoming(graph, item) else 1,
            current_y[item], id_key(item),
        ))
        for index, root in enumerate(bundle):
            place(root, cursor + subtree_above[root])
            ordered_roots.append(root)
            cursor = subtree_bounds[root][3]
            cursor += SIBLING_GAP if index + 1 < len(bundle) else MODULE_GAP
    for register_id in sorted(satellites, key=id_key):
        source = min(
            (wire.out_node for wire in graph.wires if wire.in_node == register_id),
            key=id_key,
        )
        source_rect = node_rect(source, positions, geometry)
        x = source_rect[2] + HORIZONTAL_GAP
        y = (source_rect[1] + source_rect[3] - geometry[register_id].height) / 2.0
        candidate = (x, y, x + geometry[register_id].width, y + geometry[register_id].height)
        occupied = [node_rect(item, positions, geometry) for item in positions]
        while any(overlaps_with_gap(candidate, rect, SIBLING_GAP) for rect in occupied):
            y += geometry[register_id].height + SIBLING_GAP
            candidate = (x, y, x + geometry[register_id].width, y + geometry[register_id].height)
        positions[register_id] = (round_coord(x), round_coord(y))
        subtree_bounds[register_id] = candidate
        depths[register_id] = max(0, depths[source] - 1)

    primary_keys = {(child, parent) for child, parent in primary_parent.items()}
    secondary = tuple(sorted(
        (wire.out_node, wire.out_port, wire.in_node, wire.in_port)
        for wire in graph.wires
        if wire.out_node in ids and wire.in_node in ids
        and (wire.out_node, wire.in_node) not in primary_keys
    ))
    return MeticulousLayoutPlan(
        positions=positions, primary_parent=primary_parent, children=children,
        roots=tuple(ordered_roots), depths=depths, subtree_bounds=subtree_bounds,
        secondary_edges=secondary,
    )


def apply_meticulous_layout(graph: AseGraph, plan: MeticulousLayoutPlan) -> int:
    return apply_positions(graph, plan.positions)
