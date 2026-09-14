"""Narrow data-flow matchers used by surface semantic normalization."""

from __future__ import annotations

from .model import SemanticEdge, SemanticNode, diagnostic


def _target_alpha_modulates(target: dict) -> bool:
    # Standard URP Multiply inserts its built-in half-precision AlphaModulate.
    # The exact source-alpha variant intentionally leaves modulation in the
    # graph so ASE's original float expression is preserved byte-for-byte at
    # the arithmetic boundary.
    return target.get("surface") == "Transparent" and target.get("blend") == "Multiply"


def _unresolved_modulation(report: dict, semantics: dict, node: SemanticNode, reason: str) -> None:
    semantics["unresolved"] = {
        "rule": "SEM-BLEND-001",
        "source_node": node.source_id,
        "reason": reason,
    }
    report.setdefault("diagnostics", []).append(diagnostic(
        node.source_id,
        "DUPLICATE_ALPHA_MODULATE_UNRESOLVED",
        reason,
        "The explicit ASE modulation and implicit Shader Graph Multiply modulation would both execute",
    ))


def _unproven_modulation(report: dict, semantics: dict, node: SemanticNode) -> None:
    reason = "Multiply BaseColor is fed by a Custom Function outside the certified single-assignment subset"
    semantics["unresolved"] = {
        "rule": "SEM-BLEND-001",
        "source_node": node.source_id,
        "reason": reason,
        "matcher_version": 4,
    }
    report.setdefault("diagnostics", []).append(diagnostic(
        node.source_id,
        "ALPHA_MODULATE_UNPROVEN",
        {"message": reason, "function": node.function, "precision": node.settings.get("precision", "Inherit")},
        "The exporter cannot prove that target AlphaModulate will execute exactly once",
    ))


def _single_edge_to(
    edges: list[SemanticEdge], target_id: str, target_port: int | None = None
) -> SemanticEdge | None:
    matches = [
        edge for edge in edges
        if edge.target_id == target_id
        and (target_port is None or edge.target_port == target_port)
    ]
    return matches[0] if len(matches) == 1 else None


def _input_port(node: SemanticNode, name: str) -> int | None:
    matches = [port for port, candidate in node.input_names.items() if candidate == name]
    return matches[0] if len(matches) == 1 else None


def _native_alpha_modulate(
    nodes: list[SemanticNode],
    edges: list[SemanticEdge],
    color_edge: SemanticEdge,
    alpha_edge: SemanticEdge,
) -> tuple[SemanticNode, SemanticEdge, SemanticEdge, list[SemanticNode], SemanticNode | None] | None:
    by_id = {node.target_id: node for node in nodes}
    source, route_nodes = _through_reroutes(color_edge, by_id, edges)
    node = by_id.get(source.source_id)
    if node is None or node.target_type != "lerp":
        return None
    ports = {name: _input_port(node, name) for name in ("A", "B", "T")}
    if any(value is None for value in ports.values()):
        return None
    color_input = _single_edge_to(edges, node.target_id, -1 - ports["B"])
    alpha_input = _single_edge_to(edges, node.target_id, -1 - ports["T"])
    if color_input is None or alpha_input is None:
        return None
    traced_alpha, _ = _through_reroutes(alpha_input, by_id, edges)
    surface_alpha, _ = _through_reroutes(alpha_edge, by_id, edges)
    if (traced_alpha.source_id, traced_alpha.source_port) != (
        surface_alpha.source_id,
        surface_alpha.source_port,
    ):
        return None
    white_edge = _single_edge_to(edges, node.target_id, -1 - ports["A"])
    white_node = None
    if white_edge is None:
        if not _white_value(node.defaults.get(ports["A"])):
            return None
    else:
        traced_white, _ = _through_reroutes(white_edge, by_id, edges)
        white_node = by_id.get(traced_white.source_id)
        if not _white_constant(white_node, edges):
            return None
    return node, color_input, alpha_input, route_nodes, white_node


def _through_reroutes(
    edge: SemanticEdge,
    by_id: dict[str, SemanticNode],
    edges: list[SemanticEdge],
) -> tuple[SemanticEdge, list[SemanticNode]]:
    route_nodes: list[SemanticNode] = []
    current = edge
    visited: set[str] = set()
    while current.source_id not in visited:
        visited.add(current.source_id)
        node = by_id.get(current.source_id)
        if node is None or node.target_type != "reroute":
            break
        port = _input_port(node, "In")
        incoming = _single_edge_to(edges, node.target_id, -1 - port) if port is not None else None
        if incoming is None:
            break
        route_nodes.append(node)
        current = incoming
    return current, route_nodes


def _white_constant(node: SemanticNode | None, edges: list[SemanticEdge]) -> bool:
    if node is None or node.target_type != "vector3" or node.property_name is not None:
        return False
    if any(edge.target_id == node.target_id for edge in edges):
        return False
    return all(_one(node.defaults.get(index)) for index in range(3))


def _white_value(value) -> bool:
    return isinstance(value, list) and len(value) == 3 and all(_one(item) for item in value)


def _one(value) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and float(value) == 1.0
