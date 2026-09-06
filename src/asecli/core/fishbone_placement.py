"""Geometric placement pass for a prepared recursive fishbone topology."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Mapping, Protocol

from .layout_graph import id_key, node_position, node_rect, overlaps_with_gap, round_coord, sibling_gap
from .wire_router import WIRE_NODE_TYPE

HORIZONTAL_GAP = 96.0
SIBLING_GAP = 32.0
MODULE_GAP = 96.0


class Geometry(Protocol):
    width: float
    height: float
    input_ports: dict[str, tuple[float, float]]
    output_ports: dict[str, tuple[float, float]]


@dataclass
class _Template:
    positions: dict[str, float]
    bounds: tuple[float, float, float, float]


def place_fishbone(graph, geometry: Mapping[str, Geometry], topology):
    roots = topology.roots
    main = roots[0]
    anchor_x, anchor_y = node_position(graph.node_by_id(main))
    x_by_node = {root: anchor_x for root in roots}
    stage_output_x = {}
    ordered_parents = sorted(
        topology.ids - topology.satellites,
        key=lambda node_id: (topology.depths[node_id], id_key(node_id)),
    )
    for parent in ordered_parents:
        if parent not in x_by_node:
            continue
        # Every node owns a local fishbone stage. Its direct sources share one
        # output anchor line 96px before the consumer, while independent
        # branches are not stretched to an unrelated global depth column.
        launch_x = round_coord(x_by_node[parent] - HORIZONTAL_GAP)
        for child in topology.children[parent]:
            wire = topology.primary_wire[(child, parent)]
            output_dx = geometry[child].output_ports[wire.out_port][0]
            x_by_node[child] = launch_x - output_dx
            stage_output_x[child] = launch_x

    templates: dict[str, _Template] = {}

    def build(node_id: str) -> _Template:
        if node_id in templates:
            return templates[node_id]
        positions_y = {node_id: 0.0}
        own = (
            x_by_node[node_id], 0.0,
            x_by_node[node_id] + geometry[node_id].width, geometry[node_id].height,
        )
        branch = topology.children[node_id]
        if not branch:
            templates[node_id] = _Template(positions_y, own)
            return templates[node_id]
        local = {child: build(child) for child in branch}
        spine = topology.spine_child[node_id]
        wire = topology.primary_wire[(spine, node_id)]
        shifts = {
            spine: geometry[node_id].input_ports[wire.in_port][1]
            - geometry[spine].output_ports[wire.out_port][1]
        }
        spine_bounds = _shift(local[spine].bounds, shifts[spine])
        spine_index = branch.index(spine)
        upper_cursor = min(own[1], spine_bounds[1])
        for index in range(spine_index - 1, -1, -1):
            child, next_child = branch[index], branch[index + 1]
            gap = sibling_gap(child, next_child, topology.group_of, SIBLING_GAP, MODULE_GAP)
            shifts[child] = upper_cursor - gap - local[child].bounds[3]
            upper_cursor = local[child].bounds[1] + shifts[child]
        lower_cursor = max(own[3], spine_bounds[3])
        for index in range(spine_index + 1, len(branch)):
            child, previous = branch[index], branch[index - 1]
            gap = sibling_gap(previous, child, topology.group_of, SIBLING_GAP, MODULE_GAP)
            shifts[child] = lower_cursor + gap - local[child].bounds[1]
            lower_cursor = local[child].bounds[3] + shifts[child]
        bounds = [own]
        for child in branch:
            shift = shifts[child]
            for member, y in local[child].positions.items():
                positions_y[member] = y + shift
            bounds.append(_shift(local[child].bounds, shift))
        templates[node_id] = _Template(positions_y, _union(bounds))
        return templates[node_id]

    positions, ordered_roots = {}, [main]
    main_template = build(main)
    for node_id, relative_y in main_template.positions.items():
        positions[node_id] = (round_coord(x_by_node[node_id]), round_coord(anchor_y + relative_y))
    cursor = main_template.bounds[3] + anchor_y + MODULE_GAP
    bundles: dict[tuple[str, str], list[str]] = defaultdict(list)
    for root in roots[1:]:
        owner = topology.group_of.get(root)
        bundles[("comment", owner) if owner else ("node", root)].append(root)
    ordered_bundles = sorted(
        bundles.values(),
        key=lambda bundle: (
            min(topology.current_y[item] for item in bundle), min(id_key(item) for item in bundle),
        ),
    )
    for bundle in ordered_bundles:
        bundle.sort(key=lambda item: (topology.current_y[item], id_key(item)))
        for index, root in enumerate(bundle):
            template = build(root)
            shift = cursor - template.bounds[1]
            for node_id, relative_y in template.positions.items():
                positions[node_id] = (round_coord(x_by_node[node_id]), round_coord(relative_y + shift))
            ordered_roots.append(root)
            cursor = template.bounds[3] + shift + (SIBLING_GAP if index + 1 < len(bundle) else MODULE_GAP)

    _place_registers(topology, geometry, positions)
    for node in graph.nodes:
        if node.type_name == WIRE_NODE_TYPE:
            positions[node.node_id] = node_position(node)
    return positions, ordered_roots, stage_output_x


def _place_registers(topology, geometry, positions):
    for register_id in sorted(topology.satellites, key=id_key):
        incoming = sorted(
            (wire for wire in topology.collapsed_wires if wire.in_node == register_id),
            key=lambda wire: (id_key(wire.out_node), wire.in_port),
        )
        wire = incoming[0]
        source = wire.out_node
        source_rect = node_rect(source, positions, geometry)
        x = source_rect[2] + HORIZONTAL_GAP
        source_y = positions[source][1] + geometry[source].output_ports[wire.out_port][1]
        y = source_y - geometry[register_id].input_ports[wire.in_port][1]
        candidate = (x, y, x + geometry[register_id].width, y + geometry[register_id].height)
        occupied = [node_rect(item, positions, geometry) for item in positions]
        while any(overlaps_with_gap(candidate, rect, SIBLING_GAP) for rect in occupied):
            y += geometry[register_id].height + SIBLING_GAP
            candidate = (x, y, x + geometry[register_id].width, y + geometry[register_id].height)
        positions[register_id] = round_coord(x), round_coord(y)
        topology.depths[register_id] = max(0, topology.depths[source] - 1)


def _shift(bounds, dy):
    return bounds[0], bounds[1] + dy, bounds[2], bounds[3] + dy


def _union(rects):
    values = list(rects)
    return (
        min(rect[0] for rect in values), min(rect[1] for rect in values),
        max(rect[2] for rect in values), max(rect[3] for rect in values),
    )
