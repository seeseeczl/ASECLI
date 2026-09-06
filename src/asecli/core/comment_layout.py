"""Recursive Comment fitting and quality metrics for meticulous layout."""

from __future__ import annotations

from typing import Mapping, Protocol

from .commentary import _number, inspect_comment_groups, parse_commentary_node
from .model import AseGraph

SIDE_PADDING = 30.0
TOP_PADDING = 48.0
BOTTOM_PADDING = 30.0
MODULE_GAP = 96.0


class Geometry(Protocol):
    width: float
    height: float


def refit_comments_for_layout(
    graph: AseGraph,
    geometry: Mapping[str, Geometry],
    positions: Mapping[str, tuple[float, float]],
) -> list[dict]:
    """Fit Comments, then move unrelated groups apart as intact composites."""
    if not isinstance(positions, dict):
        raise ValueError("layout positions must be mutable while fitting Comment groups")
    original = {
        group["node_id"]: {
            "position": dict(group["position"]), "width": group["width"], "height": group["height"],
        }
        for group in inspect_comment_groups(graph)
    }

    def fit_all() -> dict[str, dict]:
        groups = {group["node_id"]: group for group in inspect_comment_groups(graph)}
        fitted: set[str] = set()
        visiting: set[str] = set()

        def bounds(member_id: str):
            if member_id in groups:
                fit(member_id)
                group = groups[member_id]
                x, y = group["position"].values()
                return x, y, x + group["width"], y + group["height"]
            if member_id not in geometry or member_id not in positions:
                raise ValueError(f"layout geometry missing Comment member {member_id}")
            x, y = positions[member_id]
            return x, y, x + geometry[member_id].width, y + geometry[member_id].height

        def fit(group_id: str) -> None:
            if group_id in fitted:
                return
            if group_id in visiting:
                raise ValueError(f"comment membership contains a cycle at node {group_id}")
            visiting.add(group_id)
            group = groups[group_id]
            if not group["members"]:
                raise ValueError(f"comment {group_id} has no members to fit")
            member_bounds = [bounds(member_id) for member_id in group["members"]]
            left = min(rect[0] for rect in member_bounds) - SIDE_PADDING
            top = min(rect[1] for rect in member_bounds) - TOP_PADDING
            right = max(rect[2] for rect in member_bounds) + SIDE_PADDING
            bottom = max(rect[3] for rect in member_bounds) + BOTTOM_PADDING
            node = graph.node_by_id(group_id)
            if node is None:
                raise ValueError(f"comment node {group_id} not found")
            node.raw_fields[3] = f"{_number(left)},{_number(top)}"
            node.raw_fields[6] = _number(max(100.0, right - left))
            node.raw_fields[7] = _number(max(100.0, bottom - top))
            graph.replace_node(node)
            groups[group_id] = parse_commentary_node(node)
            visiting.remove(group_id)
            fitted.add(group_id)

        for group_id in sorted(groups, key=_id_key):
            fit(group_id)
        return groups

    groups = fit_all()
    max_moves = max(1, len(groups) * len(groups))
    for _ in range(max_moves):
        conflict = _first_group_channel_conflict(groups)
        if conflict is None:
            break
        upper_id, lower_id, dy = conflict
        del upper_id
        _move_comment_members(graph, groups, lower_id, dy, positions)
        groups = fit_all()
    else:
        raise ValueError("unable to separate unrelated Comment groups")

    final = {group["node_id"]: group for group in inspect_comment_groups(graph)}
    changes = []
    for group_id in sorted(final, key=_id_key):
        group = final[group_id]
        after = {
            "position": dict(group["position"]), "width": group["width"], "height": group["height"],
        }
        if original[group_id] != after:
            changes.append({"comment_id": group_id, "before": original[group_id], "after": after})
    return changes


def _first_group_channel_conflict(groups: dict[str, dict]):
    parent_of = {
        member: group["node_id"]
        for group in groups.values() for member in group["members"] if member in groups
    }

    def ancestors(group_id: str) -> set[str]:
        result = set()
        current = parent_of.get(group_id)
        while current is not None:
            if current in result:
                raise ValueError(f"comment membership contains a cycle at node {current}")
            result.add(current)
            current = parent_of.get(current)
        return result

    ordered = sorted(
        groups.values(),
        key=lambda group: (group["position"]["y"], group["position"]["x"], _id_key(group["node_id"])),
    )
    for index, upper in enumerate(ordered):
        upper_id = upper["node_id"]
        upper_ancestors = ancestors(upper_id)
        upper_rect = _group_rect(upper)
        for lower in ordered[index + 1:]:
            lower_id = lower["node_id"]
            if lower_id in upper_ancestors or upper_id in ancestors(lower_id):
                continue
            lower_rect = _group_rect(lower)
            x_overlap = not (
                upper_rect[2] + MODULE_GAP <= lower_rect[0]
                or lower_rect[2] + MODULE_GAP <= upper_rect[0]
            )
            y_clear = upper_rect[3] + MODULE_GAP <= lower_rect[1]
            if x_overlap and not y_clear:
                return upper_id, lower_id, upper_rect[3] + MODULE_GAP - lower_rect[1]
    return None


def _move_comment_members(graph, groups, group_id: str, dy: float, positions: dict) -> None:
    for member_id in groups[group_id]["members"]:
        if member_id in groups:
            _move_comment_members(graph, groups, member_id, dy, positions)
            continue
        if member_id not in positions:
            raise ValueError(f"layout positions missing Comment member {member_id}")
        x, y = positions[member_id]
        positions[member_id] = (x, round(y + dy, 1))
        node = graph.node_by_id(member_id)
        if node is None:
            raise ValueError(f"comment member {member_id} not found")
        node.raw_fields[3] = f"{_number(x)},{_number(round(y + dy, 1))}"
        graph.replace_node(node)


def _group_rect(group):
    x, y = group["position"].values()
    return x, y, x + group["width"], y + group["height"]


def _id_key(value: str) -> tuple[int, int | str]:
    return (0, int(value)) if value.lstrip("-").isdigit() else (1, value)
