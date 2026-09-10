"""Bind semantic endpoints to ports returned by SGCLI's configured catalog."""

from __future__ import annotations

import math
import re
from typing import Any

from .model import ExportError, SemanticEdge, SemanticNode, diagnostic, normalize, status


def bind_configured_ports(candidate: dict, report: dict, semantic_nodes: list[SemanticNode],
                          semantic_edges: list[SemanticEdge], configured: dict) -> dict:
    graph = configured.get("configured_graph")
    rows = graph.get("nodes") if isinstance(graph, dict) else None
    if not isinstance(rows, list):
        report["diagnostics"].append(diagnostic(None, "CATALOG_INVALID",
            "SGCLI configured catalog has no node manifest", "Target ports cannot be bound"))
        raise ExportError("invalid SGCLI configured catalog", report)
    bound: dict[str, dict[str, dict[int, int]]] = {}
    failed = False
    for node in semantic_nodes:
        try:
            row = _match_manifest_node(node, rows)
            bound[node.target_id] = {
                "inputs": _bind_named_ports(node.input_names, row.get("ports", []), True),
                "outputs": _bind_named_ports(
                    node.output_names, row.get("ports", []), False,
                    allow_single=node.target_type == "property",
                ),
            }
        except ValueError as exc:
            failed = True
            report["diagnostics"].append(diagnostic(node.source_id, "NODE_BINDING_FAILED", str(exc),
                                                   "Configured Shader Graph ports are unknown"))
    if failed:
        report["verification"]["target_capabilities"] = status("blocked", "configured node binding failed")
        raise ExportError("target Shader Graph capabilities could not be bound", report)

    connected_inputs = {(edge.target_id, edge.target_port) for edge in semantic_edges}
    node_specs = {item["id"]: item for item in candidate["nodes"]}
    for node in semantic_nodes:
        inputs = {}
        for port, value in node.defaults.items():
            semantic_port = -1 - port
            if (node.target_id, semantic_port) in connected_inputs:
                continue
            actual = bound[node.target_id]["inputs"].get(port)
            if actual is None:
                report["diagnostics"].append(diagnostic(node.source_id, "DEFAULT_BINDING_FAILED",
                    f"input {node.input_names.get(port, port)!r} is absent after configuration",
                    "The source default value cannot be preserved"))
                failed = True
            else:
                inputs[str(actual)] = value
                _record_configured_port(report, node.source_id, port, node.target_id, actual, input_port=True)
        if inputs:
            node_specs[node.target_id]["inputs"] = inputs

    connections = []
    for edge in semantic_edges:
        try:
            source_port = _endpoint_port(bound, rows, edge.source_id, edge.source_port, False)
            target_port = _endpoint_port(bound, rows, edge.target_id, edge.target_port, True)
        except ValueError as exc:
            report["diagnostics"].append(diagnostic(None, "PORT_BINDING_FAILED", str(exc),
                                                   "A source computation edge cannot be recreated"))
            failed = True
            continue
        connections.append({"from": [edge.source_id, source_port], "to": [edge.target_id, target_port]})
        _record_edge_ports(report, edge, source_port, target_port)
    candidate["connections"] = connections
    _check_graph(candidate, report)
    if failed or report["diagnostics"]:
        report["verification"]["target_capabilities"] = status("blocked", "target binding or structural checks failed")
        raise ExportError("target Shader Graph capabilities could not be bound", report)
    report["verification"]["target_capabilities"] = status("passed", "all configured nodes and ports bound")
    return candidate


def _match_manifest_node(node: SemanticNode, rows: list[dict]) -> dict:
    positioned = [row for row in rows if _same_position(row.get("position"), node.position)
                  and not str(row.get("type", "")).endswith("BlockNode")]
    if len(positioned) == 1:
        return positioned[0]
    aliases = {normalize(node.target_type), normalize(_native_hint(node.target_type))}
    matches = [row for row in positioned if normalize(str(row.get("name", ""))) in aliases
               or normalize(str(row.get("type", "")).rsplit(".", 1)[-1]) in aliases]
    if len(matches) != 1:
        raise ValueError(f"node {node.target_id} matched {len(matches)} configured nodes at {node.position}")
    return matches[0]


def _native_hint(alias: str) -> str:
    return {"float": "Float", "vector2": "Vector 2", "vector3": "Vector 3", "vector4": "Vector 4",
            "property": "Property", "sample-texture": "Sample Texture 2D", "uv": "UV",
            "one-minus": "One Minus"}.get(alias, alias)


def _bind_named_ports(names: dict[int, str], ports: list[dict], input_port: bool,
                      *, allow_single: bool = False) -> dict[int, int]:
    result = {}
    directional = [port for port in ports if port.get("input") is input_port
                   and type(port.get("id")) is int]
    if allow_single and len(names) == 1 and len(directional) == 1:
        return {next(iter(names)): directional[0]["id"]}
    for semantic, name in names.items():
        matches = [port for port in directional
                   if normalize(_port_name(str(port.get("name", "")))) == normalize(name)]
        if len(matches) != 1:
            raise ValueError(f"port {name!r} matched {len(matches)} configured ports")
        result[semantic] = matches[0]["id"]
    return result


def _endpoint_port(bound, rows, node_id, semantic_port, input_port):
    if node_id in bound:
        logical = -1 - semantic_port if input_port else semantic_port
        port = bound[node_id]["inputs" if input_port else "outputs"].get(logical)
        if port is None:
            raise ValueError(f"node {node_id} semantic port {semantic_port} is unavailable")
        return port
    if not input_port:
        raise ValueError(f"source node {node_id} was not configured")
    block_name = normalize(node_id.split(".")[-1])
    matches = [port for row in rows if str(row.get("type", "")).endswith("BlockNode")
               and (str(row.get("name")) == node_id
                    or normalize(str(row.get("name", "")).split(".")[-1]) == block_name)
               for port in row.get("ports", []) if port.get("input") is True and type(port.get("id")) is int]
    if len(matches) != 1:
        raise ValueError(f"output block {node_id} matched {len(matches)} configured input ports")
    return matches[0]["id"]


def _check_graph(spec: dict, report: dict) -> None:
    diagnostics = report["diagnostics"]
    ids = [row.get("id") for row in spec.get("nodes", [])]
    if len(ids) != len(set(ids)):
        diagnostics.append(diagnostic(None, "DUPLICATE_TARGET_ID", "target node ids are not unique", "References are ambiguous"))
    node_ids = set(ids)
    seen_inputs, adjacency = set(), {node_id: set() for node_id in node_ids}
    for edge in spec.get("connections", []):
        source, target = edge["from"], edge["to"]
        if source[0] not in node_ids:
            diagnostics.append(diagnostic(None, "MISSING_SOURCE", source, "Connection source is absent"))
        if target[0] not in node_ids and not str(target[0]).startswith(("SurfaceDescription.", "VertexDescription.")):
            diagnostics.append(diagnostic(None, "MISSING_TARGET", target, "Connection target is absent"))
        endpoint = tuple(target)
        if endpoint in seen_inputs:
            diagnostics.append(diagnostic(None, "DUPLICATE_TARGET_INPUT", target, "Input has multiple connections"))
        seen_inputs.add(endpoint)
        if source[0] in node_ids and target[0] in node_ids:
            adjacency[source[0]].add(target[0])
    for row in spec.get("nodes", []):
        if any((row["id"], int(port)) in seen_inputs for port in row.get("inputs", {})):
            diagnostics.append(diagnostic(None, "INPUT_CONFLICT", row["id"], "Input has a constant and a connection"))
        if not _finite_tree(row.get("inputs", {})):
            diagnostics.append(diagnostic(None, "NON_FINITE", row["id"], "Input contains a non-finite number"))
    visiting, visited = set(), set()
    def visit(node_id):
        if node_id in visiting:
            return True
        if node_id in visited:
            return False
        visiting.add(node_id)
        cyclic = any(visit(child) for child in adjacency[node_id])
        visiting.remove(node_id); visited.add(node_id)
        return cyclic
    if any(visit(node_id) for node_id in node_ids if node_id not in visited):
        diagnostics.append(diagnostic(None, "DATA_FLOW_CYCLE", "target graph contains a cycle", "Shader Graph data flow is invalid"))


def _finite_tree(value: Any) -> bool:
    if type(value) in {int, float}:
        return math.isfinite(value)
    if isinstance(value, dict):
        return all(_finite_tree(item) for item in value.values())
    if isinstance(value, list):
        return all(_finite_tree(item) for item in value)
    return True


def _same_position(left, right):
    return isinstance(left, list) and len(left) == len(right) == 2 and all(abs(float(a) - float(b)) < 0.01 for a, b in zip(left, right))


def _port_name(value: str) -> str:
    return re.sub(r"\([^()]+\)$", "", value).strip()


def _record_configured_port(report, source_id, source_port, target_id, actual, *, input_port):
    for row in report["mappings"]:
        if source_id in row["source_nodes"]:
            row.setdefault("configured_ports", []).append({"source": [source_id, source_port],
                "target": [target_id, actual], "direction": "input" if input_port else "output"})


def _record_edge_ports(report, edge, source_port, target_port):
    _record_configured_port(report, _source_owner(report, edge.source_id), edge.source_port,
                            edge.source_id, source_port, input_port=False)
    owner = _source_owner(report, edge.target_id)
    if owner:
        _record_configured_port(report, owner, edge.target_port, edge.target_id, target_port, input_port=True)


def _source_owner(report, target_id):
    for row in report["mappings"]:
        if target_id in row["target_nodes"]:
            return row["source_nodes"][0]
    return None
