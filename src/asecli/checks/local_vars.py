"""Structural checks for ASE Register/Get Local Var semantics."""

from __future__ import annotations

from ..core import (
    AseGraph,
    GET_LOCAL_VAR_TYPE,
    REGISTER_LOCAL_VAR_TYPE,
    parse_get_local_var,
    parse_register_local_var,
)


def append_local_var_issues(graph: AseGraph, issues: list[dict]) -> None:
    nodes_by_id = {node.node_id: node for node in graph.nodes}
    semantic_edges: list[tuple[str, str]] = []
    registers = {}
    for node in graph.nodes:
        if node.type_name != REGISTER_LOCAL_VAR_TYPE:
            continue
        try:
            item = parse_register_local_var(node)
        except ValueError as exc:
            issues.append(_issue("MALFORMED_LOCAL_VAR", node.node_id, str(exc)))
            continue
        registers[node.node_id] = item
        if not item["name"].strip():
            issues.append(_issue(
                "EMPTY_LOCAL_VAR_NAME", node.node_id,
                f"RegisterLocalVarNode {node.node_id} has an empty name",
            ))
        if not item["data_type"].strip():
            issues.append(_issue(
                "EMPTY_LOCAL_VAR_TYPE", node.node_id,
                f"RegisterLocalVarNode {node.node_id} has an empty data type",
            ))

    for node in graph.nodes:
        if node.type_name != GET_LOCAL_VAR_TYPE:
            continue
        try:
            item = parse_get_local_var(node)
        except ValueError as exc:
            issues.append(_issue("MALFORMED_LOCAL_VAR", node.node_id, str(exc)))
            continue
        target = nodes_by_id.get(item["register_id"])
        if target is None:
            issues.append(_issue(
                "DANGLING_LOCAL_VAR", node.node_id,
                f"GetLocalVarNode {node.node_id} references missing Register node {item['register_id']}",
            ))
            continue
        if target.type_name != REGISTER_LOCAL_VAR_TYPE:
            issues.append(_issue(
                "INVALID_LOCAL_VAR_TARGET", node.node_id,
                f"GetLocalVarNode {node.node_id} references non-Register node {item['register_id']}",
            ))
            continue
        register = registers.get(item["register_id"])
        if register is None:
            continue
        semantic_edges.append((item["register_id"], node.node_id))
        if item["name"] != register["name"]:
            issues.append(_issue(
                "LOCAL_VAR_NAME_MISMATCH", node.node_id,
                f"GetLocalVarNode {node.node_id} name {item['name']!r} does not match "
                f"Register {item['register_id']} name {register['name']!r}",
            ))
        if item["data_type"] != register["data_type"]:
            issues.append(_issue(
                "LOCAL_VAR_TYPE_MISMATCH", node.node_id,
                f"GetLocalVarNode {node.node_id} type {item['data_type']!r} does not match "
                f"Register {item['register_id']} type {register['data_type']!r}",
            ))

    _append_cycle_issues(graph, semantic_edges, issues)


def _issue(code: str, node_id: str, message: str) -> dict:
    return {"code": code, "severity": "error", "node_id": node_id, "message": message}


def _append_cycle_issues(graph: AseGraph, semantic_edges: list[tuple[str, str]], issues: list[dict]) -> None:
    adjacency: dict[str, set[str]] = {node.node_id: set() for node in graph.nodes}
    for wire in graph.wires:
        if wire.out_node in adjacency and wire.in_node in adjacency:
            adjacency[wire.out_node].add(wire.in_node)
    for source, target in semantic_edges:
        adjacency[source].add(target)

    index = 0
    indices: dict[str, int] = {}
    lowlinks: dict[str, int] = {}
    stack: list[str] = []
    on_stack: set[str] = set()
    components: list[set[str]] = []

    def visit(node_id: str) -> None:
        nonlocal index
        indices[node_id] = lowlinks[node_id] = index
        index += 1
        stack.append(node_id)
        on_stack.add(node_id)
        for target in adjacency[node_id]:
            if target not in indices:
                visit(target)
                lowlinks[node_id] = min(lowlinks[node_id], lowlinks[target])
            elif target in on_stack:
                lowlinks[node_id] = min(lowlinks[node_id], indices[target])
        if lowlinks[node_id] == indices[node_id]:
            component = set()
            while True:
                member = stack.pop()
                on_stack.remove(member)
                component.add(member)
                if member == node_id:
                    break
            components.append(component)

    for node_id in adjacency:
        if node_id not in indices:
            visit(node_id)

    semantic = set(semantic_edges)
    for component in components:
        cyclic = len(component) > 1 or any(node in adjacency[node] for node in component)
        uses_local_var = any(source in component and target in component for source, target in semantic)
        if cyclic and uses_local_var:
            members = sorted(component, key=lambda value: (not value.lstrip("-").isdigit(), value))
            issue = _issue(
                "LOCAL_VAR_REFERENCE_CYCLE", members[0],
                f"Local Var semantic references participate in a cycle: {', '.join(members)}",
            )
            issue["members"] = members
            issues.append(issue)
