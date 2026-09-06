"""Geometric hard gates for meticulous layout reports."""

from __future__ import annotations

from .commentary import _rect_overlap, inspect_comment_groups
from .wire_geometry import path_hits_rect, paths_cross, segment_hits_rect

GRID_SIZE = 256.0


def node_overlaps(rects) -> list[dict]:
    issues = []
    ids = sorted(rects, key=_id_key)
    for index, left in enumerate(ids):
        for right in ids[index + 1:]:
            overlap = _rect_overlap(rects[left], rects[right])
            if overlap is not None:
                issues.append({"node_ids": [left, right], "overlap": overlap})
    return issues


def subtree_overlaps(plan) -> list[dict]:
    issues = []
    for parent, children in plan.children.items():
        for index, left in enumerate(children):
            for right in children[index + 1:]:
                overlap = _rect_overlap(plan.subtree_bounds[left], plan.subtree_bounds[right])
                if overlap is not None:
                    issues.append({"parent_id": parent, "child_ids": [left, right], "overlap": overlap})
    return issues


def balance_errors(graph, plan, geometry) -> list[dict]:
    wire_port = _wire_ports(graph)
    result = []
    for parent, children in plan.children.items():
        if not children:
            continue
        offsets = [geometry[parent].input_ports[wire_port[(child, parent)]][1] for child in children]
        parent_y = plan.positions[parent][1] + (min(offsets) + max(offsets)) / 2.0
        top = min(plan.subtree_bounds[child][1] for child in children)
        bottom = max(plan.subtree_bounds[child][3] for child in children)
        result.append({"node_id": parent, "error": round(abs(parent_y - (top + bottom) / 2.0), 3)})
    return result


def sibling_order_violations(graph, plan) -> list[dict]:
    wire_port = _wire_ports(graph)
    issues = []
    for parent, children in plan.children.items():
        expected = sorted(children, key=lambda child: (_port_key(wire_port[(child, parent)]), _id_key(child)))
        actual = sorted(children, key=lambda child: plan.subtree_bounds[child][1])
        if expected != actual:
            issues.append({"parent_id": parent, "expected": expected, "actual": actual})
    return issues


def wire_through_nodes(paths, rects) -> list[dict]:
    issues = []
    grid = {}
    for node_id, rect in rects.items():
        for cell in _rect_cells(rect):
            grid.setdefault(cell, set()).add(node_id)
    for wire, path in paths:
        hit = set()
        for left, right in zip(path, path[1:]):
            segment_box = (min(left[0], right[0]), min(left[1], right[1]),
                           max(left[0], right[0]), max(left[1], right[1]))
            candidates = set()
            for cell in _rect_cells(segment_box):
                candidates.update(grid.get(cell, ()))
            for node_id in candidates - hit - {wire.out_node, wire.in_node}:
                if segment_hits_rect(left, right, rects[node_id]):
                    hit.add(node_id)
        issues.extend({"wire": wire_key(wire), "node_id": node_id} for node_id in sorted(hit, key=_id_key))
    return issues


def wire_through_comment_titles(graph, paths) -> list[dict]:
    issues = []
    groups = {group["node_id"]: group for group in inspect_comment_groups(graph)}
    related: dict[str, set[str]] = {}

    def members(group_id):
        if group_id not in related:
            values = set(groups[group_id]["members"])
            for member_id in tuple(values):
                if member_id in groups:
                    values.update(members(member_id))
            related[group_id] = values
        return related[group_id]

    for group in groups.values():
        x, y = group["position"]["x"], group["position"]["y"]
        title_rect = (x, y, x + group["width"], y + 48.0)
        for wire, path in paths:
            if {wire.out_node, wire.in_node} & members(group["node_id"]):
                continue
            if _bounds_intersect(_path_bounds(path), title_rect) and path_hits_rect(path, title_rect):
                issues.append({"wire": wire_key(wire), "comment_id": group["node_id"], "area": "title"})
    return issues


def wire_crossings(paths) -> list[list[str]]:
    issues = []
    boxed = [(wire, path, _path_bounds(path)) for wire, path in paths]
    for index, (left_wire, left_path, left_box) in enumerate(boxed):
        left_nodes = {left_wire.out_node, left_wire.in_node}
        for right_wire, right_path, right_box in boxed[index + 1:]:
            if (not left_nodes & {right_wire.out_node, right_wire.in_node}
                    and _bounds_intersect(left_box, right_box)
                    and paths_cross(left_path, right_path)):
                issues.append([wire_key(left_wire), wire_key(right_wire)])
    return issues


def _wire_ports(graph):
    result = {}
    for wire in graph.wires:
        key = (wire.out_node, wire.in_node)
        if key not in result or _port_key(wire.in_port) < _port_key(result[key]):
            result[key] = wire.in_port
    return result


def wire_key(wire) -> str:
    return f"{wire.out_node}:{wire.out_port}->{wire.in_node}:{wire.in_port}"


def _path_bounds(path):
    return (
        min(point[0] for point in path), min(point[1] for point in path),
        max(point[0] for point in path), max(point[1] for point in path),
    )


def _bounds_intersect(left, right):
    return not (left[2] < right[0] or right[2] < left[0] or left[3] < right[1] or right[3] < left[1])


def _rect_cells(rect):
    left, top, right, bottom = (int(value // GRID_SIZE) for value in rect)
    return ((x, y) for x in range(left, right + 1) for y in range(top, bottom + 1))


def _port_key(value: str):
    try:
        return 0, float(value)
    except ValueError:
        return 1, value


def _id_key(value: str):
    return (0, int(value)) if value.lstrip("-").isdigit() else (1, value)
