"""Public recursive fishbone layout plan and application API."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Protocol

from .commentary import inspect_comment_groups
from .fishbone_placement import place_fishbone
from .fishbone_topology import build_fishbone_topology
from .layout import apply_positions
from .layout_graph import id_key, node_rect
from .model import AseGraph
from .wire_router import WIRE_NODE_TYPE, plan_wire_routes


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
    ordered_children: dict[str, tuple[str, ...]]
    spine_child: dict[str, str]
    roots: tuple[str, ...]
    depths: dict[str, int]
    stage_output_x: dict[str, float]
    subtree_bounds: dict[str, tuple[float, float, float, float]]
    horizontal_edges: tuple[tuple[str, str, str, str], ...]
    secondary_edges: tuple[tuple[str, str, str, str], ...]
    comment_snapshot: tuple[tuple[str, tuple[str, ...], str], ...]
    wire_route_changes: tuple[dict, ...] = ()


def meticulous_layout_positions(
    graph: AseGraph,
    geometry: Mapping[str, Geometry],
    *,
    route_wires: bool = False,
) -> MeticulousLayoutPlan:
    topology = build_fishbone_topology(graph, geometry)
    positions, roots, stage_output_x = place_fishbone(graph, geometry, topology)
    subtree_bounds = {}
    for node_id in sorted(topology.ids, key=id_key):
        members = _descendants(node_id, topology.children)
        rects = [
            node_rect(member, positions, geometry)
            for member in members if member in positions and member in geometry
        ]
        subtree_bounds[node_id] = _union_bounds(rects)
    horizontal_edges = tuple(sorted(
        (
            child, topology.primary_wire[(child, parent)].out_port,
            parent, topology.primary_wire[(child, parent)].in_port,
        )
        for parent, child in topology.spine_child.items()
        if topology.group_of.get(parent) == topology.group_of.get(child)
    ))
    primary_keys = set(topology.primary_parent.items())
    secondary = tuple(sorted(
        (wire.out_node, wire.out_port, wire.in_node, wire.in_port)
        for wire in topology.collapsed_wires
        if wire.out_node in topology.ids and wire.in_node in topology.ids
        and (wire.out_node, wire.in_node) not in primary_keys
    ))
    comments = tuple(sorted(
        (group["node_id"], tuple(group["members"]), group["color"])
        for group in inspect_comment_groups(graph)
    ))
    route_changes = plan_wire_routes(graph, geometry, positions) if route_wires else ()
    return MeticulousLayoutPlan(
        positions=positions,
        primary_parent=topology.primary_parent,
        children=topology.children,
        ordered_children=topology.children,
        spine_child=topology.spine_child,
        roots=tuple(roots),
        depths=topology.depths,
        stage_output_x=stage_output_x,
        subtree_bounds=subtree_bounds,
        horizontal_edges=horizontal_edges,
        secondary_edges=secondary,
        comment_snapshot=comments,
        wire_route_changes=route_changes,
    )


def apply_meticulous_layout(graph: AseGraph, plan: MeticulousLayoutPlan) -> int:
    return apply_positions(graph, plan.positions)


def _union_bounds(rects):
    values = list(rects)
    return (
        min(rect[0] for rect in values), min(rect[1] for rect in values),
        max(rect[2] for rect in values), max(rect[3] for rect in values),
    )


def _descendants(node_id: str, children: Mapping[str, tuple[str, ...]]) -> set[str]:
    result, stack = {node_id}, list(children.get(node_id, ()))
    while stack:
        child = stack.pop()
        if child not in result:
            result.add(child)
            stack.extend(children.get(child, ()))
    return result
