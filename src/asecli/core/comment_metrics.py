"""Whitespace, outlier, and positioned-bound metrics for ASE Comments."""

from __future__ import annotations

from typing import Mapping, Protocol

from .commentary import inspect_comment_groups
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


def comment_layout_metrics(
    graph: AseGraph,
    geometry: Mapping[str, Geometry],
    positions: Mapping[str, tuple[float, float]],
) -> tuple[list[dict], list[dict]]:
    groups = {group["node_id"]: group for group in inspect_comment_groups(graph)}

    def bounds(member_id: str) -> tuple[float, float, float, float]:
        if member_id in groups:
            group = groups[member_id]
            x, y = group["position"].values()
            return x, y, x + group["width"], y + group["height"]
        x, y = positions[member_id]
        return x, y, x + geometry[member_id].width, y + geometry[member_id].height

    whitespace, outliers = [], []
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
                rect[0] - HORIZONTAL_FOOTPRINT, rect[1] - VERTICAL_FOOTPRINT,
                rect[2] + HORIZONTAL_FOOTPRINT, rect[3] + VERTICAL_FOOTPRINT,
            ), content_rect)
            for _, rect in member_bounds
        ]
        occupied = _rect_union_area([rect for rect in footprints if _area(rect) > 0])
        ratio = max(0.0, 1.0 - min(1.0, occupied / frame_area))
        whitespace.append({
            "comment_id": group_id,
            "ratio": round(ratio, 4),
            "status": "error" if ratio > WHITESPACE_ERROR else (
                "warning" if ratio > WHITESPACE_TARGET else "passed"
            ),
        })
        if len(member_bounds) < 2:
            continue
        full = _union(rect for _, rect in member_bounds)
        full_area = _area(full)
        for member_id, _ in member_bounds:
            remaining = [rect for item_id, rect in member_bounds if item_id != member_id]
            reduction = 0.0 if full_area == 0 else 1.0 - _area(_union(remaining)) / full_area
            if reduction > 0.35:
                outliers.append({
                    "comment_id": group_id, "member_id": member_id,
                    "area_reduction_if_removed": round(reduction, 4),
                })
    return whitespace, outliers


def positioned_bounds(geometry, positions):
    return {
        node_id: (x, y, geometry[node_id].width, geometry[node_id].height)
        for node_id, (x, y) in positions.items() if node_id in geometry
    }


def _union(rects):
    values = list(rects)
    return (
        min(rect[0] for rect in values), min(rect[1] for rect in values),
        max(rect[2] for rect in values), max(rect[3] for rect in values),
    )


def _area(rect):
    return max(0.0, rect[2] - rect[0]) * max(0.0, rect[3] - rect[1])


def _clip(rect, bounds):
    return (
        max(rect[0], bounds[0]), max(rect[1], bounds[1]),
        min(rect[2], bounds[2]), min(rect[3], bounds[3]),
    )


def _rect_union_area(rects):
    if not rects:
        return 0.0
    xs = sorted({value for rect in rects for value in (rect[0], rect[2])})
    area = 0.0
    for left, right in zip(xs, xs[1:]):
        spans = sorted(
            (rect[1], rect[3]) for rect in rects
            if rect[0] < right and rect[2] > left and rect[3] > rect[1]
        )
        if right <= left or not spans:
            continue
        start, end = spans[0]
        covered = 0.0
        for top, bottom in spans[1:]:
            if top > end:
                covered += end - start
                start, end = top, bottom
            else:
                end = max(end, bottom)
        area += (right - left) * (covered + end - start)
    return area


def _id_key(value: str):
    return (0, int(value)) if value.lstrip("-").isdigit() else (1, value)
