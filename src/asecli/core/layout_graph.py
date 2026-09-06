"""Shared graph and geometry helpers for meticulous layout."""

from __future__ import annotations

from typing import Mapping

from .commentary import inspect_comment_groups
from .layout import MASTER_TYPES
from .model import AseGraph, WireLine


def graph_depths(ids: set[str], outgoing: Mapping[str, list[WireLine]]) -> dict[str, int]:
    memo: dict[str, int] = {}
    def visit(node_id: str) -> int:
        if node_id not in memo:
            consumers = [wire.in_node for wire in outgoing.get(node_id, [])]
            memo[node_id] = 0 if not consumers else 1 + max(visit(item) for item in consumers)
        return memo[node_id]
    for node_id in sorted(ids, key=id_key):
        visit(node_id)
    return memo


def reject_cycles(ids: set[str], outgoing: Mapping[str, list[WireLine]]) -> None:
    state: dict[str, int] = {}
    def visit(node_id: str) -> None:
        if state.get(node_id) == 1:
            raise ValueError(f"data-flow cycle detected at node {node_id}")
        if state.get(node_id) == 2:
            return
        state[node_id] = 1
        for wire in outgoing.get(node_id, []):
            visit(wire.in_node)
        state[node_id] = 2
    for node_id in sorted(ids, key=id_key):
        visit(node_id)


def require_connected_ports(graph: AseGraph, geometry, ids: set[str]) -> None:
    for wire in graph.wires:
        if wire.out_node not in ids or wire.in_node not in ids:
            continue
        if wire.out_port not in geometry[wire.out_node].output_ports:
            raise ValueError(f"editor geometry missing output port {wire.out_node}:{wire.out_port}")
        if wire.in_port not in geometry[wire.in_node].input_ports:
            raise ValueError(f"editor geometry missing input port {wire.in_node}:{wire.in_port}")


def immediate_comment_owners(graph: AseGraph) -> dict[str, str]:
    return {member: group["node_id"] for group in inspect_comment_groups(graph) for member in group["members"]}


def sibling_gap(left: str, right: str, owners: Mapping[str, str], normal: float, module: float) -> float:
    crosses_group = owners.get(left) != owners.get(right) and (owners.get(left) or owners.get(right))
    return module if crosses_group else normal


def alignment_offset(node_id, branch, primary_wire, geometry) -> float:
    offsets = [geometry[node_id].input_ports[primary_wire[(child, node_id)].in_port][1] for child in branch]
    return (min(offsets) + max(offsets)) / 2.0 if offsets else geometry[node_id].height / 2.0


def descendants(node_id: str, children: Mapping[str, tuple[str, ...]]) -> set[str]:
    result, stack = {node_id}, list(children[node_id])
    while stack:
        child = stack.pop()
        if child not in result:
            result.add(child)
            stack.extend(children[child])
    return result


def node_rect(node_id: str, positions, geometry) -> tuple[float, float, float, float]:
    x, y = positions[node_id]
    return x, y, x + geometry[node_id].width, y + geometry[node_id].height


def overlaps_with_gap(left, right, gap: float) -> bool:
    return not (left[2] + gap <= right[0] or right[2] + gap <= left[0]
                or left[3] + gap <= right[1] or right[3] + gap <= left[1])


def node_position(node) -> tuple[float, float]:
    if node is None:
        raise ValueError("layout node not found")
    try:
        return tuple(float(value) for value in node.raw_fields[3].split(","))  # type: ignore[return-value]
    except (IndexError, ValueError) as exc:
        raise ValueError(f"node {node.node_id} has invalid x,y position") from exc


def is_master(graph: AseGraph, node_id: str) -> bool:
    node = graph.node_by_id(node_id)
    return node is not None and node.type_name in MASTER_TYPES


def has_incoming(graph: AseGraph, node_id: str) -> bool:
    return any(wire.in_node == node_id for wire in graph.wires)


def port_key(value: str) -> tuple[int, float | str]:
    try:
        return 0, float(value)
    except ValueError:
        return 1, value


def id_key(value: str) -> tuple[int, int | str]:
    return (0, int(value)) if value.lstrip("-").isdigit() else (1, value)


def round_coord(value: float) -> float:
    return round(value, 1)
