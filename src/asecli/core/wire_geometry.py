"""Approximate ASE Bezier paths for deterministic layout diagnostics."""

from __future__ import annotations

from typing import Mapping, Protocol

from .model import AseGraph, WireLine


class Geometry(Protocol):
    width: float
    height: float
    input_ports: dict[str, tuple[float, float]]
    output_ports: dict[str, tuple[float, float]]


def wire_paths(
    graph: AseGraph,
    geometry: Mapping[str, Geometry],
    positions: Mapping[str, tuple[float, float]],
    *,
    samples: int = 24,
) -> list[tuple[WireLine, list[tuple[float, float]]]]:
    result = []
    for wire in graph.wires:
        if wire.out_node not in positions or wire.in_node not in positions:
            continue
        source = _anchor(wire.out_node, wire.out_port, True, geometry, positions)
        target = _anchor(wire.in_node, wire.in_port, False, geometry, positions)
        span = max(48.0, abs(target[0] - source[0]) * 0.5)
        control_a = (source[0] + span, source[1])
        control_b = (target[0] - span, target[1])
        path = [_bezier(source, control_a, control_b, target, step / samples) for step in range(samples + 1)]
        result.append((wire, path))
    return result


def path_hits_rect(path: list[tuple[float, float]], rect: tuple[float, float, float, float]) -> bool:
    return any(segment_hits_rect(left, right, rect) for left, right in zip(path, path[1:]))


def segment_hits_rect(a, b, rect) -> bool:
    left, top, right, bottom = rect
    if left <= a[0] <= right and top <= a[1] <= bottom:
        return True
    if left <= b[0] <= right and top <= b[1] <= bottom:
        return True
    corners = [(left, top), (right, top), (right, bottom), (left, bottom)]
    return any(_segments_cross(a, b, corners[index], corners[(index + 1) % 4]) for index in range(4))


def paths_cross(left: list[tuple[float, float]], right: list[tuple[float, float]]) -> bool:
    for a, b in zip(left, left[1:]):
        for c, d in zip(right, right[1:]):
            if _segments_cross(a, b, c, d):
                return True
    return False


def _anchor(node_id, port_id, output, geometry, positions) -> tuple[float, float]:
    offsets = geometry[node_id].output_ports if output else geometry[node_id].input_ports
    dx, dy = offsets[port_id]
    x, y = positions[node_id]
    return x + dx, y + dy


def _bezier(p0, p1, p2, p3, t: float) -> tuple[float, float]:
    one = 1.0 - t
    return (
        one ** 3 * p0[0] + 3 * one * one * t * p1[0] + 3 * one * t * t * p2[0] + t ** 3 * p3[0],
        one ** 3 * p0[1] + 3 * one * one * t * p1[1] + 3 * one * t * t * p2[1] + t ** 3 * p3[1],
    )


def _segments_cross(a, b, c, d) -> bool:
    def orient(p, q, r):
        return (q[0] - p[0]) * (r[1] - p[1]) - (q[1] - p[1]) * (r[0] - p[0])
    ab_c, ab_d = orient(a, b, c), orient(a, b, d)
    cd_a, cd_b = orient(c, d, a), orient(c, d, b)
    epsilon = 1e-6
    return ((ab_c > epsilon and ab_d < -epsilon) or (ab_c < -epsilon and ab_d > epsilon)) and (
        (cd_a > epsilon and cd_b < -epsilon) or (cd_a < -epsilon and cd_b > epsilon)
    )
