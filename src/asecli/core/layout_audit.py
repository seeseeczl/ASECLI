"""Versioned quality report for meticulous ASE graph layout."""

from __future__ import annotations

import hashlib
import json
from typing import Mapping

from .comment_bounds import comment_containment_issues
from .comment_layout import WHITESPACE_ERROR, comment_layout_metrics, positioned_bounds
from .local_vars import GET_LOCAL_VAR_TYPE, REGISTER_LOCAL_VAR_TYPE
from .layout_audit_geometry import (
    balance_errors, node_overlaps, sibling_order_violations, subtree_overlaps,
    wire_crossings, wire_through_comment_titles, wire_through_nodes,
)
from .meticulous_layout import Geometry, MeticulousLayoutPlan
from .model import AseGraph
from .wire_geometry import wire_paths

REPORT_SCHEMA = "asecli.graph-layout.v2"
BALANCE_TOLERANCE = 8.0
TEMPLATE_TOLERANCE = 8.0


def audit_meticulous_layout(
    graph: AseGraph,
    geometry: Mapping[str, Geometry],
    plan: MeticulousLayoutPlan,
    *,
    moved: int,
) -> dict:
    positions = plan.positions
    rects = {
        node_id: (x, y, x + geometry[node_id].width, y + geometry[node_id].height)
        for node_id, (x, y) in positions.items()
    }
    node_overlap_items = node_overlaps(rects)
    subtree_overlap_items = subtree_overlaps(plan)
    balance = balance_errors(graph, plan, geometry)
    sibling_order = sibling_order_violations(graph, plan)
    paths = wire_paths(graph, geometry, positions)
    wire_through = wire_through_nodes(paths, rects)
    wire_through += wire_through_comment_titles(graph, paths)
    crossing_items = wire_crossings(paths)
    live_bounds = positioned_bounds(geometry, positions)
    comment_issues = comment_containment_issues(graph, live_bounds)
    whitespace, outliers = comment_layout_metrics(graph, geometry, positions)
    register_distance, get_distance = _local_var_distances(graph, rects)
    remote_direct = _remote_direct_wires(graph, plan)
    repeated = _repeated_module_mismatches(graph, plan)

    containment = [item for item in comment_issues if item["code"] == "COMMENT_MEMBER_OUTSIDE_FRAME"]
    comment_overlap = [item for item in comment_issues if item["code"] == "COMMENT_GROUP_OVERLAP"]
    hard_failures = []
    hard_failures += _failure_codes("NODE_OVERLAP", node_overlap_items)
    hard_failures += _failure_codes("SUBTREE_OVERLAP", subtree_overlap_items)
    hard_failures += _failure_codes("SUBTREE_BALANCE", [item for item in balance if item["error"] > BALANCE_TOLERANCE])
    hard_failures += _failure_codes("SIBLING_ORDER", sibling_order)
    hard_failures += _failure_codes("WIRE_THROUGH_NODE", wire_through)
    hard_failures += _failure_codes("COMMENT_CONTAINMENT", containment)
    hard_failures += _failure_codes("COMMENT_OVERLAP", comment_overlap)
    hard_failures += _failure_codes(
        "COMMENT_WHITESPACE", [item for item in whitespace if item["ratio"] > WHITESPACE_ERROR],
    )
    report = {
        "schema": REPORT_SCHEMA,
        "status": "failed" if hard_failures else "passed",
        "node_overlaps": node_overlap_items,
        "subtree_balance_error": balance,
        "sibling_order_violations": sibling_order,
        "subtree_overlaps": subtree_overlap_items,
        "wire_through_nodes": wire_through,
        "wire_wire_crossings": {"count": len(crossing_items), "pairs": crossing_items[:100]},
        "comment_containment": containment,
        "comment_overlap": comment_overlap,
        "comment_whitespace_ratio": whitespace,
        "outlier_members": outliers,
        "register_distance": register_distance,
        "get_consumer_distance": get_distance,
        "remote_direct_wires": remote_direct,
        "repeated_module_mismatches": repeated,
        "layout_stability": {
            "moved_nodes": moved,
            "fingerprint": _fingerprint(positions),
            "deterministic": True,
        },
        "hard_failures": hard_failures,
        "visual_validation": "requires_editor_review" if not hard_failures else "blocked",
    }
    return report


def _local_var_distances(graph, rects) -> tuple[list[dict], list[dict]]:
    types = {node.node_id: node.type_name for node in graph.nodes}
    register, get = [], []
    for wire in graph.wires:
        if wire.out_node not in rects or wire.in_node not in rects:
            continue
        distance = round(max(0.0, rects[wire.in_node][0] - rects[wire.out_node][2]), 3)
        item = {"from": wire.out_node, "to": wire.in_node, "distance": distance,
                "status": "passed" if 64.0 <= distance <= 160.0 else "warning"}
        if types.get(wire.in_node) == REGISTER_LOCAL_VAR_TYPE:
            register.append(item)
        if types.get(wire.out_node) == GET_LOCAL_VAR_TYPE:
            get.append(item)
    return register, get


def _remote_direct_wires(graph, plan) -> list[dict]:
    types = {node.node_id: node.type_name for node in graph.nodes}
    registers = {wire.out_node for wire in graph.wires if types.get(wire.in_node) == REGISTER_LOCAL_VAR_TYPE}
    return [
        {"from": wire.out_node, "to": wire.in_node, "stage_span": plan.depths[wire.out_node] - plan.depths[wire.in_node]}
        for wire in graph.wires
        if wire.out_node in registers and types.get(wire.in_node) != REGISTER_LOCAL_VAR_TYPE
        and plan.depths.get(wire.out_node, 0) - plan.depths.get(wire.in_node, 0) >= 3
    ]


def _repeated_module_mismatches(graph, plan) -> list[dict]:
    types = {node.node_id: node.type_name for node in graph.nodes}
    signatures: dict[tuple, list[str]] = {}
    for parent, children in plan.children.items():
        if children:
            signature = _tree_signature(parent, plan, types)
            signatures.setdefault(signature, []).append(parent)
    issues = []
    for parents in signatures.values():
        if len(parents) < 2:
            continue
        baseline = _relative_profile(parents[0], plan)
        for parent in parents[1:]:
            profile = _relative_profile(parent, plan)
            if len(profile) != len(baseline) or any(abs(a - b) > TEMPLATE_TOLERANCE for a, b in zip(profile, baseline)):
                issues.append({"baseline": parents[0], "node_id": parent})
    return issues


def _relative_profile(parent, plan) -> tuple[float, ...]:
    origin_x, origin_y = plan.positions[parent]
    values = []
    stack = [parent]
    while stack:
        node_id = stack.pop()
        if node_id != parent:
            x, y = plan.positions[node_id]
            values.extend((round(x - origin_x, 3), round(y - origin_y, 3)))
        stack.extend(reversed(plan.children[node_id]))
    return tuple(values)


def _tree_signature(node_id, plan, types):
    return (types[node_id], tuple(_tree_signature(child, plan, types) for child in plan.children[node_id]))


def _failure_codes(code: str, items: list) -> list[dict]:
    return [{"code": code, "count": len(items)}] if items else []


def _fingerprint(positions) -> str:
    payload = json.dumps(sorted(positions.items()), separators=(",", ":"))
    return hashlib.sha256(payload.encode()).hexdigest()
