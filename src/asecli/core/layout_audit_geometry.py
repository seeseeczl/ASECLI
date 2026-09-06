"""Geometric hard gates for meticulous layout reports."""

from __future__ import annotations

from .commentary import _rect_overlap, inspect_comment_groups
from .layout_graph import id_key, port_key
from .wire_geometry import path_hits_rect, paths_cross, segment_hits_rect
from .wire_router import logical_wires

GRID_SIZE = 256.0


def node_overlaps(rects) -> list[dict]:
    issues = []
    ids = sorted(rects, key=id_key)
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
    result = []
    for parent, children in plan.children.items():
        if not children:
            continue
        spine = plan.spine_child[parent]
        index = children.index(spine)
        upper = children[:index]
        lower = children[index + 1:]
        axis = _edge_y(graph, plan, geometry, spine, parent)[1]
        upper_height = 0.0 if not upper else axis - min(plan.subtree_bounds[item][1] for item in upper)
        lower_height = 0.0 if not lower else max(plan.subtree_bounds[item][3] for item in lower) - axis
        result.append({
            "node_id": parent,
            "spine_child": spine,
            "upper_height": round(max(0.0, upper_height), 3),
            "lower_height": round(max(0.0, lower_height), 3),
            "error": round(abs(upper_height - lower_height), 3),
        })
    return result


def stage_right_alignment(graph, plan, geometry, *, tolerance: float = 8.0) -> list[dict]:
    result = []
    for parent, children in sorted(plan.children.items(), key=lambda item: id_key(item[0])):
        if not children:
            continue
        expected = plan.stage_output_x[children[0]]
        deviations = []
        for child in children:
            wire = _primary_wire(graph, child, parent)
            actual = plan.positions[child][0] + geometry[child].output_ports[wire.out_port][0]
            error = abs(actual - expected)
            if error > tolerance:
                deviations.append({"node_id": child, "error": round(error, 3)})
        if deviations:
            result.append({"parent_id": parent, "expected_x": expected, "nodes": deviations})
    return result


def spine_horizontal_errors(graph, plan, geometry, *, tolerance: float = 8.0) -> list[dict]:
    issues = []
    for child, out_port, parent, in_port in plan.horizontal_edges:
        source_y = plan.positions[child][1] + geometry[child].output_ports[out_port][1]
        target_y = plan.positions[parent][1] + geometry[parent].input_ports[in_port][1]
        error = abs(source_y - target_y)
        if error > tolerance:
            issues.append({
                "from": child, "to": parent,
                "out_port": out_port, "in_port": in_port,
                "error": round(error, 3),
            })
    return issues


def branch_side_balance(plan) -> list[dict]:
    result = []
    for parent, children in plan.children.items():
        if not children:
            continue
        spine = plan.spine_child[parent]
        index = children.index(spine)
        result.append({
            "node_id": parent,
            "spine_child": spine,
            "upper_count": index,
            "lower_count": len(children) - index - 1,
            "count_difference": abs(index - (len(children) - index - 1)),
        })
    return result


def horizontal_edge_ratio(graph, plan, geometry, *, tolerance: float = 8.0) -> dict:
    total = horizontal = 0
    for child, parent in plan.primary_parent.items():
        wire = _primary_wire(graph, child, parent)
        source_y, target_y = _edge_y(graph, plan, geometry, child, parent, wire=wire)
        total += 1
        horizontal += abs(source_y - target_y) <= tolerance
    return {
        "horizontal": horizontal,
        "total": total,
        "ratio": 1.0 if total == 0 else round(horizontal / total, 4),
    }


def stage_gap_violations(graph, plan, geometry, *, minimum: float = 64.0, maximum: float = 160.0) -> list[dict]:
    issues = []
    for child, parent in plan.primary_parent.items():
        source_right = plan.positions[child][0] + geometry[child].width
        target_left = plan.positions[parent][0]
        gap = target_left - source_right
        if gap < minimum or gap > maximum:
            issues.append({
                "from": child, "to": parent, "gap": round(gap, 3),
                "minimum": minimum, "maximum": maximum,
            })
    return issues


def sibling_order_violations(graph, plan) -> list[dict]:
    wire_port = _wire_ports(graph)
    issues = []
    for parent, children in plan.children.items():
        expected = sorted(children, key=lambda child: (port_key(wire_port[(child, parent)]), id_key(child)))
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
        issues.extend({"wire": wire_key(wire), "node_id": node_id} for node_id in sorted(hit, key=id_key))
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
        if key not in result or port_key(wire.in_port) < port_key(result[key]):
            result[key] = wire.in_port
    return result


def _primary_wire(graph, child, parent):
    choices = [
        item.wire for item in logical_wires(graph)
        if item.wire.out_node == child and item.wire.in_node == parent
    ]
    if not choices:
        raise ValueError(f"primary layout edge {child}->{parent} is missing")
    return min(choices, key=lambda wire: (port_key(wire.in_port), port_key(wire.out_port)))


def _edge_y(graph, plan, geometry, child, parent, *, wire=None):
    wire = wire or _primary_wire(graph, child, parent)
    return (
        plan.positions[child][1] + geometry[child].output_ports[wire.out_port][1],
        plan.positions[parent][1] + geometry[parent].input_ports[wire.in_port][1],
    )


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
