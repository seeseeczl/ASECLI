"""ASE Register/Get Local Var semantic references."""

from __future__ import annotations

from .model import AseGraph, NodeLine


REGISTER_LOCAL_VAR_TYPE = "AmplifyShaderEditor.RegisterLocalVarNode"
GET_LOCAL_VAR_TYPE = "AmplifyShaderEditor.GetLocalVarNode"


def parse_register_local_var(node: NodeLine) -> dict:
    if node.type_name != REGISTER_LOCAL_VAR_TYPE:
        raise ValueError(f"node {node.node_id} is not a RegisterLocalVarNode")
    if len(node.raw_fields) < 16:
        raise ValueError(f"RegisterLocalVarNode {node.node_id} has too few serialized fields")
    return {
        "node_id": node.node_id,
        "name": node.raw_fields[6],
        "data_type": node.raw_fields[15],
    }


def parse_get_local_var(node: NodeLine) -> dict:
    if node.type_name != GET_LOCAL_VAR_TYPE:
        raise ValueError(f"node {node.node_id} is not a GetLocalVarNode")
    if len(node.raw_fields) < 15:
        raise ValueError(f"GetLocalVarNode {node.node_id} has too few serialized fields")
    return {
        "node_id": node.node_id,
        "register_id": node.raw_fields[6],
        "name": node.raw_fields[7],
        "data_type": node.raw_fields[14],
    }


def local_var_edges(graph: AseGraph) -> list[tuple[str, str]]:
    """Return valid semantic data-flow edges as ``Register -> Get``."""
    registers = {
        node.node_id
        for node in graph.nodes
        if node.type_name == REGISTER_LOCAL_VAR_TYPE
    }
    edges = []
    for node in graph.nodes:
        if node.type_name != GET_LOCAL_VAR_TYPE:
            continue
        try:
            item = parse_get_local_var(node)
        except ValueError:
            continue
        if item["register_id"] in registers:
            edges.append((item["register_id"], node.node_id))
    return edges
