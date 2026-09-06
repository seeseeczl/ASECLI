"""Recursive Comment fitting and quality metrics for meticulous layout."""

from __future__ import annotations

from typing import Mapping, Protocol

from .commentary import _number, inspect_comment_groups, parse_commentary_node
from .model import AseGraph

SIDE_PADDING = 30.0
TOP_PADDING = 48.0
BOTTOM_PADDING = 30.0
WHITESPACE_TARGET = 0.55
WHITESPACE_ERROR = 0.65
HORIZONTAL_FOOTPRINT = 48.0
VERTICAL_FOOTPRINT = 16.0


class Geometry(Protocol):
    width: float
    height: float


def refit_comments_for_layout(
    graph: AseGraph,
    geometry: Mapping[str, Geometry],
    positions: Mapping[str, tuple[float, float]],
) -> list[dict]:
    """Fit nested comments from the inside out using asymmetric title padding."""
    groups = {group["node_id"]: group for group in inspect_comment_groups(graph)}
    fitted: set[str] = set()
    visiting: set[str] = set()
    changes: list[dict] = []

    def bounds(member_id: str) -> tuple[float, float, float, float]:
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
        before = {
            "position": dict(group["position"]), "width": group["width"], "height": group["height"],
        }
        after = {
            "position": {"x": left, "y": top},
            "width": max(100.0, right - left), "height": max(100.0, bottom - top),
        }
        node = graph.node_by_id(group_id)
        if node is None:
            raise ValueError(f"comment node {group_id} not found")
        node.raw_fields[3] = f"{_number(left)},{_number(top)}"
        node.raw_fields[6] = _number(after["width"])
        node.raw_fields[7] = _number(after["height"])
        graph.replace_node(node)
        groups[group_id] = parse_commentary_node(node)
        if before != after:
            changes.append({"comment_id": group_id, "before": before, "after": after})
        visiting.remove(group_id)
        fitted.add(group_id)

    for group_id in sorted(groups, key=_id_key):
        fit(group_id)
    return changes


def comment_layout_metrics(
    graph: AseGraph,
    geometry: Mapping[str, Geometry],
    positions: Mapping[str, tuple[float, float]],
) -> tuple[list[dict], list[dict]]:
    """Return whitespace and direct-member outlier diagnostics after refitting."""
    groups = {group["node_id"]: group for group in inspect_comment_groups(graph)}

    def bounds(member_id: str) -> tuple[float, float, float, float]:
        if member_id in groups:
            group = groups[member_id]
            x, y = group["position"].values()
            return x, y, x + group["width"], y + group["height"]
        x, y = positions[member_id]
        return x, y, x + geometry[member_id].width, y + geometry[member_id].height

    whitespace: list[dict] = []
    outliers: list[dict] = []
    for group_id in sorted(groups, key=_id_key):
        group = groups[group_id]
        frame_area = group["width"] * group["height"]
        member_bounds = [(member_id, bounds(member_id)) for member_id in group["members"]]
        content_rect = (
            group["position"]["x"] + SIDE_PADDING,
            group["position"]["y"] + TOP_PADDING,
            group["position"]["x"] + group["width"] - SIDE_PADDING,
            group["position"]["y"] + group["height"] - BOTTOM_PADDING,
        )
        footprints = [
            _clip((
                rect[0] - HORIZONTAL_FOOTPRINT,
                rect[1] - VERTICAL_FOOTPRINT,
                rect[2] + HORIZONTAL_FOOTPRINT,
                rect[3] + VERTICAL_FOOTPRINT,
            ), content_rect)
            for _, rect in member_bounds
        ]
        occupied_area = _rect_union_area([rect for rect in footprints if _area(rect) > 0])
        ratio = max(0.0, 1.0 - min(1.0, occupied_area / frame_area))
        whitespace.append({
            "comment_id": group_id,
            "ratio": round(ratio, 4),
            "status": "error" if ratio > WHITESPACE_ERROR else "warning" if ratio > WHITESPACE_TARGET else "passed",
        })
        if len(member_bounds) < 2:
            continue
        full = _union(rect for _, rect in member_bounds)
        full_area = _area(full)
        for member_id, _ in member_bounds:
            remaining = [rect for item_id, rect in member_bounds if item_id != member_id]
            reduced_area = _area(_union(remaining))
            reduction = 0.0 if full_area == 0 else 1.0 - reduced_area / full_area
            if reduction > 0.35:
                outliers.append({
                    "comment_id": group_id, "member_id": member_id,
                    "area_reduction_if_removed": round(reduction, 4),
                })
    return whitespace, outliers


def positioned_bounds(
    geometry: Mapping[str, Geometry], positions: Mapping[str, tuple[float, float]],
) -> dict[str, tuple[float, float, float, float]]:
    return {
        node_id: (x, y, geometry[node_id].width, geometry[node_id].height)
        for node_id, (x, y) in positions.items()
    }


def _union(rects) -> tuple[float, float, float, float]:
    values = list(rects)
    return (
        min(rect[0] for rect in values), min(rect[1] for rect in values),
        max(rect[2] for rect in values), max(rect[3] for rect in values),
    )


def _area(rect: tuple[float, float, float, float]) -> float:
    return max(0.0, rect[2] - rect[0]) * max(0.0, rect[3] - rect[1])


def _clip(rect, bounds):
    return (
        max(rect[0], bounds[0]), max(rect[1], bounds[1]),
        min(rect[2], bounds[2]), min(rect[3], bounds[3]),
    )


def _rect_union_area(rects) -> float:
    """Exact union area for the small rectangle sets inside one Comment."""
    if not rects:
        return 0.0
    xs = sorted({value for rect in rects for value in (rect[0], rect[2])})
    area = 0.0
    for left, right in zip(xs, xs[1:]):
        if right <= left:
            continue
        spans = sorted(
            (rect[1], rect[3]) for rect in rects
            if rect[0] < right and rect[2] > left and rect[3] > rect[1]
        )
        covered = 0.0
        if spans:
            start, end = spans[0]
            for top, bottom in spans[1:]:
                if top > end:
                    covered += end - start
                    start, end = top, bottom
                else:
                    end = max(end, bottom)
            covered += end - start
        area += (right - left) * covered
    return area


def _id_key(value: str) -> tuple[int, int | str]:
    return (0, int(value)) if value.lstrip("-").isdigit() else (1, value)
