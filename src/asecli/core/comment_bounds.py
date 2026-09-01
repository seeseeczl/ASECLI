"""Editor-accurate containment checks and resizing for ASE Comment frames."""

from __future__ import annotations

from .commentary import (
    NodeBounds,
    _node_bounds,
    _number,
    _rect_overlap,
    inspect_comment_groups,
    parse_commentary_node,
)
from .model import AseGraph


def comment_containment_issues(
    graph: AseGraph,
    node_bounds: dict[str, NodeBounds],
    *,
    tolerance: float = 0.01,
) -> list[dict]:
    """Report members outside frames and unrelated Comment frames that overlap."""
    issues: list[dict] = []
    groups = inspect_comment_groups(graph)
    for group in groups:
        frame = (
            group["position"]["x"], group["position"]["y"],
            group["position"]["x"] + group["width"],
            group["position"]["y"] + group["height"],
        )
        for member_id in group["members"]:
            member = graph.node_by_id(member_id)
            if member is None:
                continue
            bounds = _node_bounds(member, node_bounds)
            overflow = {
                "left": max(0.0, frame[0] - bounds[0]),
                "top": max(0.0, frame[1] - bounds[1]),
                "right": max(0.0, bounds[2] - frame[2]),
                "bottom": max(0.0, bounds[3] - frame[3]),
            }
            overflow = {key: round(value, 3) for key, value in overflow.items() if value > tolerance}
            if overflow:
                issues.append({
                    "code": "COMMENT_MEMBER_OUTSIDE_FRAME",
                    "severity": "warning",
                    "comment_id": group["node_id"],
                    "comment_title": group["title"],
                    "member_id": member_id,
                    "overflow": overflow,
                    "message": f"comment {group['node_id']} does not fully contain member {member_id}",
                })
    group_ids = {group["node_id"] for group in groups}
    children = {
        group["node_id"]: [member_id for member_id in group["members"] if member_id in group_ids]
        for group in groups
    }

    def is_ancestor(ancestor_id: str, descendant_id: str) -> bool:
        stack = list(children[ancestor_id])
        visited: set[str] = set()
        while stack:
            current = stack.pop()
            if current == descendant_id:
                return True
            if current in visited:
                raise ValueError(f"comment membership contains a cycle at node {current}")
            visited.add(current)
            stack.extend(children[current])
        return False

    frames = {
        group["node_id"]: (
            group["position"]["x"],
            group["position"]["y"],
            group["position"]["x"] + group["width"],
            group["position"]["y"] + group["height"],
        )
        for group in groups
    }
    for index, left in enumerate(groups):
        for right in groups[index + 1:]:
            left_id, right_id = left["node_id"], right["node_id"]
            if is_ancestor(left_id, right_id) or is_ancestor(right_id, left_id):
                continue
            overlap = _rect_overlap(frames[left_id], frames[right_id], tolerance=tolerance)
            if overlap is not None:
                issues.append({
                    "code": "COMMENT_GROUP_OVERLAP",
                    "severity": "warning",
                    "comment_ids": [left_id, right_id],
                    "comment_titles": [left["title"], right["title"]],
                    "overlap": overlap,
                    "message": f"unrelated comment groups {left_id} and {right_id} overlap",
                })
    return issues


def refit_comment_groups(
    graph: AseGraph,
    node_bounds: dict[str, NodeBounds],
    *,
    padding: float = 50.0,
    group_ids: list[str] | None = None,
) -> list[dict]:
    """Resize frames around live bounds without moving members."""
    if not 0 <= padding <= 1000:
        raise ValueError("padding must be between 0 and 1000")
    groups = {group["node_id"]: group for group in inspect_comment_groups(graph)}
    selected = set(groups) if group_ids is None else {str(value) for value in group_ids}
    missing = sorted(selected - set(groups), key=_node_id_sort_key)
    if missing:
        raise KeyError(f"comment node(s) not found: {', '.join(missing)}")
    changes: list[dict] = []
    fitted: set[str] = set()
    visiting: set[str] = set()

    def fit(group_id: str) -> None:
        if group_id in fitted:
            return
        if group_id in visiting:
            raise ValueError(f"comment membership contains a cycle at node {group_id}")
        visiting.add(group_id)
        group = groups[group_id]
        bounds: list[NodeBounds] = []
        for member_id in group["members"]:
            member = graph.node_by_id(member_id)
            if member is None:
                raise KeyError(f"node {member_id} not found")
            if member_id in groups and member_id in selected:
                fit(member_id)
            bounds.append(_node_bounds(member, node_bounds))
        if not bounds:
            raise ValueError(f"comment {group_id} has no members to fit")
        min_x, min_y = min(item[0] for item in bounds), min(item[1] for item in bounds)
        max_x, max_y = max(item[2] for item in bounds), max(item[3] for item in bounds)
        after = {
            "position": {"x": min_x - padding, "y": min_y - padding},
            "width": max(100.0, max_x - min_x + 2 * padding),
            "height": max(100.0, max_y - min_y + 2 * padding),
        }
        before = {
            "position": dict(group["position"]),
            "width": group["width"], "height": group["height"],
        }
        node = graph.node_by_id(group_id)
        assert node is not None
        node.raw_fields[3] = f"{_number(after['position']['x'])},{_number(after['position']['y'])}"
        node.raw_fields[6], node.raw_fields[7] = _number(after["width"]), _number(after["height"])
        graph.replace_node(node)
        groups[group_id] = parse_commentary_node(node)
        if before != after:
            changes.append({
                "comment_id": group_id, "title": group["title"],
                "before": before, "after": after,
            })
        visiting.remove(group_id)
        fitted.add(group_id)

    for group_id in sorted(selected, key=_node_id_sort_key):
        fit(group_id)
    return changes


def _node_id_sort_key(value: str) -> tuple[int, int | str]:
    return (0, int(value)) if value.lstrip("-").isdigit() else (1, value)
