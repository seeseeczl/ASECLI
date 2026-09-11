"""Bind certified ASE semantics directly to SGCLI native v3 slot names."""

from __future__ import annotations

import math
from typing import Any

from .model import ExportError, SemanticEdge, SemanticNode, diagnostic, status


OUTPUT_SLOTS = {
    "SurfaceDescription.BakedGI": "Baked GI",
    "SurfaceDescription.Emission": "Emission",
    "SurfaceDescription.BaseColor": "Base Color",
    "SurfaceDescription.Alpha": "Alpha",
    "SurfaceDescription.AlphaClipThreshold": "Alpha Clip Threshold",
    "VertexDescription.Position": "Position",
    "VertexDescription.Normal": "Normal",
    "SurfaceDescription.AlphaClipThresholdShadow": "Alpha Clip Threshold Shadow",
}


def bind_named_ports(
    candidate: dict,
    report: dict,
    semantic_nodes: list[SemanticNode],
    semantic_edges: list[SemanticEdge],
) -> dict:
    """Finish a bare ``sgcli.native.v3`` spec without invoking SGCLI."""
    by_id = {node.target_id: node for node in semantic_nodes}
    node_specs = {item["id"]: item for item in candidate["nodes"]}
    connected_inputs = {(edge.target_id, edge.target_port) for edge in semantic_edges}
    failed = False

    for node in semantic_nodes:
        inputs: dict[str, Any] = {}
        for port, value in node.defaults.items():
            semantic_port = -1 - port
            if (node.target_id, semantic_port) in connected_inputs:
                continue
            name = node.input_names.get(port)
            if not name:
                report["diagnostics"].append(diagnostic(
                    node.source_id,
                    "DEFAULT_BINDING_FAILED",
                    f"input {port} has no certified SGCLI slot name",
                    "The source default value cannot be preserved",
                ))
                failed = True
                continue
            if name in inputs:
                report["diagnostics"].append(diagnostic(
                    node.source_id,
                    "DEFAULT_BINDING_FAILED",
                    f"input slot name {name!r} is duplicated",
                    "The source default value cannot be preserved unambiguously",
                ))
                failed = True
                continue
            inputs[name] = value
            _record_named_port(report, node.source_id, port, node.target_id, name, input_port=True)
        if inputs:
            node_specs[node.target_id]["inputs"] = inputs

    connections = []
    for edge in semantic_edges:
        source_name = _node_slot(by_id, edge.source_id, edge.source_port, input_port=False)
        target_name = _target_slot(by_id, edge.target_id, edge.target_port)
        if source_name is None or target_name is None:
            report["diagnostics"].append(diagnostic(
                None,
                "PORT_BINDING_FAILED",
                f"no certified named binding for {edge.source_id}:{edge.source_port} -> "
                f"{edge.target_id}:{edge.target_port}",
                "A source computation edge cannot be recreated",
            ))
            failed = True
            continue
        connections.append({
            "from": [edge.source_id, source_name],
            "to": [edge.target_id, target_name],
        })
        _record_named_edge(report, edge, source_name, target_name)

    candidate["connections"] = connections
    _check_graph(candidate, report)
    if failed or report["diagnostics"]:
        report["verification"]["target_capabilities"] = status(
            "blocked", "named-slot binding or structural checks failed"
        )
        raise ExportError("target Shader Graph named slots could not be bound", report)
    report["verification"]["target_capabilities"] = status(
        "not_run", "SGCLI resolves named slots against the target Editor when it consumes the spec"
    )
    return candidate


def _node_slot(
    by_id: dict[str, SemanticNode], node_id: str, semantic_port: int, *, input_port: bool
) -> str | None:
    node = by_id.get(node_id)
    if node is None:
        return None
    logical = -1 - semantic_port if input_port else semantic_port
    names = node.input_names if input_port else node.output_names
    return names.get(logical)


def _target_slot(
    by_id: dict[str, SemanticNode], node_id: str, semantic_port: int
) -> str | None:
    if node_id in by_id:
        return _node_slot(by_id, node_id, semantic_port, input_port=True)
    return OUTPUT_SLOTS.get(node_id)


def _check_graph(spec: dict, report: dict) -> None:
    diagnostics = report["diagnostics"]
    ids = [row.get("id") for row in spec.get("nodes", [])]
    if len(ids) != len(set(ids)):
        diagnostics.append(diagnostic(
            None, "DUPLICATE_TARGET_ID", "target node ids are not unique", "References are ambiguous"
        ))
    node_ids = set(ids)
    seen_inputs: set[tuple[Any, Any]] = set()
    adjacency = {node_id: set() for node_id in node_ids}
    for edge in spec.get("connections", []):
        source, target = edge["from"], edge["to"]
        if source[0] not in node_ids:
            diagnostics.append(diagnostic(None, "MISSING_SOURCE", source, "Connection source is absent"))
        if target[0] not in node_ids and target[0] not in OUTPUT_SLOTS:
            diagnostics.append(diagnostic(None, "MISSING_TARGET", target, "Connection target is absent"))
        endpoint = tuple(target)
        if endpoint in seen_inputs:
            diagnostics.append(diagnostic(
                None, "DUPLICATE_TARGET_INPUT", target, "Input has multiple connections"
            ))
        seen_inputs.add(endpoint)
        if source[0] in node_ids and target[0] in node_ids:
            adjacency[source[0]].add(target[0])
    for row in spec.get("nodes", []):
        if any((row["id"], name) in seen_inputs for name in row.get("inputs", {})):
            diagnostics.append(diagnostic(
                None, "INPUT_CONFLICT", row["id"], "Input has a constant and a connection"
            ))
        if not _finite_tree(row.get("inputs", {})):
            diagnostics.append(diagnostic(
                None, "NON_FINITE", row["id"], "Input contains a non-finite number"
            ))

    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(node_id: str) -> bool:
        if node_id in visiting:
            return True
        if node_id in visited:
            return False
        visiting.add(node_id)
        cyclic = any(visit(child) for child in adjacency[node_id])
        visiting.remove(node_id)
        visited.add(node_id)
        return cyclic

    if any(visit(node_id) for node_id in node_ids if node_id not in visited):
        diagnostics.append(diagnostic(
            None, "DATA_FLOW_CYCLE", "target graph contains a cycle", "Shader Graph data flow is invalid"
        ))


def _finite_tree(value: Any) -> bool:
    if type(value) in {int, float}:
        return math.isfinite(value)
    if isinstance(value, dict):
        return all(_finite_tree(item) for item in value.values())
    if isinstance(value, list):
        return all(_finite_tree(item) for item in value)
    return True


def _record_named_port(
    report: dict,
    source_id: str,
    source_port: int,
    target_id: str,
    name: str,
    *,
    input_port: bool,
) -> None:
    for row in report["mappings"]:
        if source_id in row["source_nodes"]:
            row.setdefault("named_ports", []).append({
                "source": [source_id, source_port],
                "target": [target_id, name],
                "direction": "input" if input_port else "output",
            })


def _record_named_edge(
    report: dict, edge: SemanticEdge, source_name: str, target_name: str
) -> None:
    source_owner = _source_owner(report, edge.source_id)
    if source_owner:
        _record_named_port(
            report, source_owner, edge.source_port, edge.source_id, source_name, input_port=False
        )
    target_owner = _source_owner(report, edge.target_id)
    if target_owner:
        _record_named_port(
            report, target_owner, edge.target_port, edge.target_id, target_name, input_port=True
        )


def _source_owner(report: dict, target_id: str) -> str | None:
    for row in report["mappings"]:
        if target_id in row["target_nodes"] and row["source_nodes"]:
            return row["source_nodes"][0]
    return None
