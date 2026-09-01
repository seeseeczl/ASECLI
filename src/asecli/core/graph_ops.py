"""Graph mutation operations (TASK-0007)."""

from __future__ import annotations

from .model import AseGraph, NodeLine, WireLine
from .local_vars import GET_LOCAL_VAR_TYPE, REGISTER_LOCAL_VAR_TYPE, parse_get_local_var


def set_node_field(graph: AseGraph, node_id: str, field_index: int, value: str) -> NodeLine:
    """Set one serialized field of a node by absolute index (0 = 'Node' marker)."""
    if field_index in {0, 1, 2}:
        raise ValueError(
            "fields 0-2 are structural (marker/type/id) and cannot be changed with set-field"
        )
    node = graph.node_by_id(node_id)
    if node is None:
        raise KeyError(f"node {node_id} not found")
    if not 0 <= field_index < len(node.raw_fields):
        raise IndexError(f"field index {field_index} out of range (node has {len(node.raw_fields)} fields)")
    node.raw_fields[field_index] = value
    graph.replace_node(node)
    return node


def remove_node(graph: AseGraph, node_id: str) -> int:
    """Remove a node and every wire touching it. Returns removed wire count."""
    target = graph.node_by_id(node_id)
    if target is None:
        raise KeyError(f"node {node_id} not found")
    if target.type_name == REGISTER_LOCAL_VAR_TYPE:
        references = []
        for node in graph.nodes:
            if node.type_name != GET_LOCAL_VAR_TYPE:
                continue
            try:
                if parse_get_local_var(node)["register_id"] == node_id:
                    references.append(node.node_id)
            except ValueError:
                continue
        if references:
            rendered = ", ".join(sorted(references, key=_node_id_sort_key))
            raise ValueError(f"RegisterLocalVarNode {node_id} is referenced by Get nodes: {rendered}")
    removed_wires = 0
    for i in reversed(range(len(graph.instructions))):
        kind, raw = graph.instructions[i]
        if kind == "wire":
            w = _parse_wire(raw)
            if w.in_node == node_id or w.out_node == node_id:
                graph.delete_instruction(i)
                removed_wires += 1
    for i, (kind, raw) in enumerate(graph.instructions):
        if kind == "node" and _parse_node(raw).node_id == node_id:
            graph.delete_instruction(i)
            return removed_wires
    raise KeyError(f"node {node_id} not found")


def _node_id_sort_key(value: str) -> tuple[int, int | str]:
    return (0, int(value)) if value.lstrip("-").isdigit() else (1, value)


def connect(
    graph: AseGraph,
    src_node: str,
    src_port: str,
    dst_node: str,
    dst_port: str,
) -> WireLine:
    """Wire source output port to destination input port (creates data flow src -> dst)."""
    if graph.node_by_id(src_node) is None:
        raise KeyError(f"source node {src_node} not found")
    if graph.node_by_id(dst_node) is None:
        raise KeyError(f"destination node {dst_node} not found")
    for w in graph.wires:
        if (w.in_node, w.in_port, w.out_node, w.out_port) == (dst_node, dst_port, src_node, src_port):
            return w  # already connected
        if (w.in_node, w.in_port) == (dst_node, dst_port):
            raise ValueError(
                f"destination input {dst_node}:{dst_port} is already connected from "
                f"{w.out_node}:{w.out_port}"
            )
    wire = WireLine(in_node=dst_node, in_port=dst_port, out_node=src_node, out_port=src_port)
    graph.add_wire(wire)
    return wire


def disconnect(graph: AseGraph, src_node: str, src_port: str, dst_node: str, dst_port: str) -> bool:
    return graph.remove_wire(
        out_node=src_node, out_port=src_port, in_node=dst_node, in_port=dst_port
    )


def next_free_node_id(graph: AseGraph) -> int:
    used = {int(n.node_id) for n in graph.nodes if n.node_id.lstrip("-").isdigit()}
    candidate = 1
    while candidate in used:
        candidate += 1
    return candidate


def node_from_schema(graph: AseGraph, schema: dict, node_id: int | None, pos: str, type_name: str) -> NodeLine:
    """Build a NodeLine from a runtime schema (schema['fields'] excludes the 6-field prefix)."""
    if node_id is None:
        node_id = next_free_node_id(graph)
    fixed_fields = list(schema.get("fixed_fields", ["Inherit", "False"]))
    if len(fixed_fields) != 2 or schema.get("fixed_prefix_len", 6) != 6:
        raise ValueError(f"unsupported fixed node prefix for {type_name}")
    fields = ["Node", type_name, str(node_id), pos, *fixed_fields]
    fields.extend(schema["fields"])
    return NodeLine(type_name=type_name, node_id=str(node_id), raw_fields=fields)


def _parse_wire(raw: str) -> WireLine:
    from .model import _parse_wire_line

    return _parse_wire_line(raw)


def _parse_node(raw: str) -> NodeLine:
    from .model import parse_node_line

    return parse_node_line(raw)
