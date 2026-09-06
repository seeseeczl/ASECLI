"""Versioned quality report for meticulous ASE graph layout."""

from __future__ import annotations

import hashlib
import json
from typing import Mapping

from .comment_bounds import comment_containment_issues
from .comment_metrics import WHITESPACE_ERROR, comment_layout_metrics, positioned_bounds
from .local_vars import GET_LOCAL_VAR_TYPE, REGISTER_LOCAL_VAR_TYPE
from .layout_graph import immediate_comment_owners
from .layout_audit_geometry import (
    balance_errors, branch_side_balance, horizontal_edge_ratio, node_overlaps,
    sibling_order_violations, spine_horizontal_errors, stage_gap_violations,
    stage_right_alignment, subtree_overlaps, wire_crossings,
    wire_through_comment_titles, wire_through_nodes,
)
from .layout_audit_repeated import repeated_module_mismatches
from .commentary import inspect_comment_groups
from .meticulous_layout import Geometry, MeticulousLayoutPlan
from .model import AseGraph
from .wire_router import logical_wires, routed_wire_paths

REPORT_SCHEMA = "asecli.graph-layout.v2"


def audit_meticulous_layout(
    graph: AseGraph,
    geometry: Mapping[str, Geometry],
    plan: MeticulousLayoutPlan,
    *,
    moved: int,
    comment_purpose: list[dict] | None = None,
) -> dict:
    positions = plan.positions
    _refresh_subtree_bounds(plan, geometry)
    rects = {
        node_id: (x, y, x + geometry[node_id].width, y + geometry[node_id].height)
        for node_id, (x, y) in positions.items()
        if node_id in geometry
    }
    node_overlap_items = node_overlaps(rects)
    subtree_overlap_items = subtree_overlaps(plan)
    balance = balance_errors(graph, plan, geometry)
    stage_alignment = stage_right_alignment(graph, plan, geometry)
    spine_alignment = spine_horizontal_errors(graph, plan, geometry)
    side_balance = branch_side_balance(plan)
    horizontal_ratio = horizontal_edge_ratio(graph, plan, geometry)
    gap_violations = stage_gap_violations(graph, plan, geometry)
    sibling_order = sibling_order_violations(graph, plan)
    paths = routed_wire_paths(graph, geometry, positions, plan.wire_route_changes)
    wire_through = wire_through_nodes(paths, rects)
    wire_through += wire_through_comment_titles(graph, paths)
    crossing_items = wire_crossings(paths)
    live_bounds = positioned_bounds(geometry, positions)
    comment_issues = comment_containment_issues(graph, live_bounds)
    whitespace, outliers = comment_layout_metrics(graph, geometry, positions)
    register_distance, get_distance = _local_var_distances(graph, rects)
    remote_direct = _remote_direct_wires(graph, plan)
    repeated = repeated_module_mismatches(graph, plan)
    comment_preservation = _comment_preservation(graph, plan)
    purpose = (
        comment_purpose
        if comment_purpose is not None
        else _existing_comment_purpose(graph)
    )

    containment = [item for item in comment_issues if item["code"] == "COMMENT_MEMBER_OUTSIDE_FRAME"]
    comment_overlap = [item for item in comment_issues if item["code"] == "COMMENT_GROUP_OVERLAP"]
    hard_failures = []
    hard_failures += _failure_codes("NODE_OVERLAP", node_overlap_items)
    hard_failures += _failure_codes("SUBTREE_OVERLAP", subtree_overlap_items)
    hard_failures += _failure_codes("STAGE_RIGHT_ALIGNMENT", stage_alignment)
    hard_failures += _failure_codes("SPINE_HORIZONTAL", spine_alignment)
    hard_failures += _failure_codes(
        "BRANCH_SIDE_BALANCE", [item for item in side_balance if item["count_difference"] > 1],
    )
    hard_failures += _failure_codes("STAGE_GAP", gap_violations)
    hard_failures += _failure_codes("SIBLING_ORDER", sibling_order)
    hard_failures += _failure_codes("WIRE_THROUGH_NODE", wire_through)
    hard_failures += _failure_codes("COMMENT_CONTAINMENT", containment)
    hard_failures += _failure_codes("COMMENT_OVERLAP", comment_overlap)
    hard_failures += _failure_codes(
        "COMMENT_WHITESPACE", [item for item in whitespace if item["ratio"] > WHITESPACE_ERROR],
    )
    hard_failures += _failure_codes("COMMENT_PRESERVATION", comment_preservation["issues"])
    hard_failures += _failure_codes(
        "COMMENT_PURPOSE_UNRESOLVED", [item for item in purpose if item["status"] == "unresolved"],
    )
    report = {
        "schema": REPORT_SCHEMA,
        "status": "failed" if hard_failures else "passed",
        "node_overlaps": node_overlap_items,
        "subtree_balance_error": balance,
        "stage_right_alignment": stage_alignment,
        "spine_horizontal_error": spine_alignment,
        "branch_side_balance": side_balance,
        "horizontal_edge_ratio": horizontal_ratio,
        "stage_gap_violations": gap_violations,
        "sibling_order_violations": sibling_order,
        "subtree_overlaps": subtree_overlap_items,
        "wire_through_nodes": wire_through,
        "wire_wire_crossings": {"count": len(crossing_items), "pairs": crossing_items[:100]},
        "residual_wire_crossings": {"count": len(crossing_items), "pairs": crossing_items[:100]},
        "comment_containment": containment,
        "comment_overlap": comment_overlap,
        "comment_whitespace_ratio": whitespace,
        "comment_preservation": comment_preservation,
        "comment_purpose": purpose,
        "outlier_members": outliers,
        "register_distance": register_distance,
        "get_consumer_distance": get_distance,
        "remote_direct_wires": remote_direct,
        "repeated_module_mismatches": repeated,
        "wire_route_changes": list(plan.wire_route_changes),
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
    for item in logical_wires(graph):
        wire = item.wire
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


def _refresh_subtree_bounds(plan, geometry) -> None:
    for node_id in plan.children:
        members, stack = {node_id}, list(plan.children.get(node_id, ()))
        while stack:
            child = stack.pop()
            if child not in members:
                members.add(child)
                stack.extend(plan.children.get(child, ()))
        rects = [
            (
                plan.positions[member][0], plan.positions[member][1],
                plan.positions[member][0] + geometry[member].width,
                plan.positions[member][1] + geometry[member].height,
            )
            for member in members if member in plan.positions and member in geometry
        ]
        plan.subtree_bounds[node_id] = (
            min(rect[0] for rect in rects), min(rect[1] for rect in rects),
            max(rect[2] for rect in rects), max(rect[3] for rect in rects),
        )


def _remote_direct_wires(graph, plan) -> list[dict]:
    types = {node.node_id: node.type_name for node in graph.nodes}
    owners = immediate_comment_owners(graph)
    direct_wires = [
        item.wire for item in logical_wires(graph)
        if types.get(item.wire.out_node) != GET_LOCAL_VAR_TYPE
        and types.get(item.wire.in_node) != REGISTER_LOCAL_VAR_TYPE
    ]
    consumer_groups: dict[str, set[str]] = {}
    for wire in direct_wires:
        owner = owners.get(wire.in_node)
        if owner is not None:
            consumer_groups.setdefault(wire.out_node, set()).add(owner)

    result = []
    for wire in direct_wires:
        groups = consumer_groups.get(wire.out_node, set())
        consumer_group = owners.get(wire.in_node)
        producer_group = owners.get(wire.out_node)
        if len(groups) < 2 or consumer_group is None:
            continue
        # Once two or more algorithm groups consume the source, it is a module
        # interface. Local uses inside the producer's own group may stay direct;
        # every other known group must consume it through a nearby Get.
        if producer_group is not None and consumer_group == producer_group:
            continue
        result.append({
            "from": wire.out_node,
            "to": wire.in_node,
            "stage_span": plan.depths.get(wire.out_node, 0) - plan.depths.get(wire.in_node, 0),
            "producer_group": producer_group,
            "consumer_group": consumer_group,
            "consumer_groups": sorted(groups),
            "reason": "consumed_by_multiple_groups",
        })
    return result


def _comment_preservation(graph, plan) -> dict:
    current = tuple(sorted(
        (group["node_id"], tuple(group["members"]), group["color"])
        for group in inspect_comment_groups(graph)
    ))
    expected = plan.comment_snapshot
    issues = []
    expected_by_id = {item[0]: item for item in expected}
    current_by_id = {item[0]: item for item in current}
    for comment_id in sorted(set(expected_by_id) | set(current_by_id)):
        if comment_id not in current_by_id:
            issues.append({"comment_id": comment_id, "code": "deleted"})
        elif comment_id not in expected_by_id:
            issues.append({"comment_id": comment_id, "code": "added"})
        elif current_by_id[comment_id][1:] != expected_by_id[comment_id][1:]:
            issues.append({"comment_id": comment_id, "code": "membership_or_color_changed"})
    return {"status": "passed" if not issues else "failed", "issues": issues}


def _existing_comment_purpose(graph) -> list[dict]:
    return [
        {"comment_id": group["node_id"], "status": "existing", "title": group["title"]}
        for group in inspect_comment_groups(graph)
    ]


def _failure_codes(code: str, items: list) -> list[dict]:
    return [{"code": code, "count": len(items)}] if items else []


def _fingerprint(positions) -> str:
    payload = json.dumps(sorted(positions.items()), separators=(",", ":"))
    return hashlib.sha256(payload.encode()).hexdigest()
