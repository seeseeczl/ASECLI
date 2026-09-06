"""Declarative, atomic material-property ordering and ASECLI metadata specs."""

from __future__ import annotations

from .custom_gui import (
    SUPPORTED_GUI_EDITORS,
    graph_custom_editor,
    is_material_property_node,
    remove_property_metadata_attribute,
    semantic_attribute,
    set_custom_editor,
    set_property_metadata_attribute,
)
from .custom_gui_versions import require_property_metadata_tail_version
from .material_gui_condition import enable_if_attribute, validate_enable_if
from .model import AseFile, AseGraph, NodeLine
from .property_presentation import set_property_display_name


_TOP_KEYS = {"editor", "reorder", "properties"}
_PROPERTY_KEYS = {
    "name", "node", "display_name", "group", "help", "tooltip", "enabled_if"
}
_SEMANTIC_TYPES = {
    "group": "FoldoutMzgui",
    "help": "HelpBoxMzgui",
    "tooltip": "TooltipMzgui",
}


def material_property_nodes(graph: AseGraph) -> list[NodeLine]:
    return [node for node in graph.nodes if is_material_property_node(node)]


def resolve_property_node(
    graph: AseGraph,
    *,
    node_id: str | None = None,
    property_name: str | None = None,
) -> NodeLine:
    """Resolve an exported property by node id or exact ShaderLab property name."""
    if (node_id is None) == (property_name is None):
        raise ValueError("provide exactly one of node id or property name")
    if node_id is not None:
        node = graph.node_by_id(node_id)
        if node is None:
            raise KeyError(f"node {node_id} not found")
        if not is_material_property_node(node):
            raise ValueError(f"node {node_id} is not an exported PropertyNode")
        return node
    matches = [node for node in material_property_nodes(graph) if node.raw_fields[7] == property_name]
    if len(matches) != 1:
        raise ValueError(f"expected one exported property named {property_name!r}, found {len(matches)}")
    return matches[0]


def apply_material_gui_spec(ase_file: AseFile, spec: dict) -> list[dict]:
    """Apply a declarative property order/group/tooltip/optional-help spec in memory."""
    if not isinstance(spec, dict):
        raise ValueError("material GUI spec root must be a JSON object")
    unknown = set(spec) - _TOP_KEYS
    if unknown:
        raise ValueError(f"unknown material GUI spec keys: {sorted(unknown)}")
    entries = spec.get("properties", [])
    if not isinstance(entries, list):
        raise ValueError("material GUI spec 'properties' must be an array")
    reorder = spec.get("reorder", False)
    if not isinstance(reorder, bool):
        raise ValueError("material GUI spec 'reorder' must be boolean")

    changes: list[dict] = []
    editor = spec.get("editor")
    if editor is not None:
        if not isinstance(editor, str):
            raise ValueError("material GUI spec 'editor' must be a class-name string")
        changes.append(set_custom_editor(ase_file, editor))

    resolved: list[tuple[NodeLine, dict]] = []
    seen: set[str] = set()
    has_additions = False
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            raise ValueError(f"properties[{index}] must be an object")
        unknown = set(entry) - _PROPERTY_KEYS
        if unknown:
            raise ValueError(f"properties[{index}] has unknown keys: {sorted(unknown)}")
        has_name = "name" in entry
        has_node = "node" in entry
        if has_name == has_node:
            raise ValueError(f"properties[{index}] must provide exactly one of 'name' or 'node'")
        if has_name and not isinstance(entry["name"], str):
            raise ValueError(f"properties[{index}] field 'name' must be a string")
        if has_node and not isinstance(entry["node"], (str, int)):
            raise ValueError(f"properties[{index}] field 'node' must be a string or integer")
        node = resolve_property_node(
            ase_file.graph,
            node_id=str(entry["node"]) if has_node else None,
            property_name=entry.get("name"),
        )
        if node.node_id in seen:
            raise ValueError(f"property node {node.node_id} appears more than once in spec")
        seen.add(node.node_id)
        resolved.append((node, entry))
        has_additions |= any(entry.get(key) is not None for key in _SEMANTIC_TYPES if key in entry)
        has_additions |= entry.get("enabled_if") is not None

    active_editor = graph_custom_editor(ase_file.graph)
    if has_additions and active_editor not in SUPPORTED_GUI_EDITORS:
        supported = ", ".join(sorted(SUPPORTED_GUI_EDITORS))
        raise ValueError(f"MZGUI-compatible property metadata requires a selected material GUI: {supported}")
    if reorder and not resolved:
        raise ValueError("reorder=true requires at least one property entry")
    if reorder:
        require_property_metadata_tail_version(ase_file.graph)
        changes.extend(_reorder_properties(ase_file.graph, [node for node, _ in resolved]))

    for node, entry in resolved:
        if "display_name" in entry:
            display_name = entry["display_name"]
            if not isinstance(display_name, str):
                raise ValueError(
                    f"property {node.raw_fields[7]} field 'display_name' must be a string"
                )
            changes.append(set_property_display_name(ase_file, node.node_id, display_name))
        for key, type_name in _SEMANTIC_TYPES.items():
            if key not in entry:
                continue
            value = entry[key]
            if value is None:
                changes.append(remove_property_metadata_attribute(ase_file.graph, node.node_id, type_name))
            elif isinstance(value, str):
                changes.append(
                    set_property_metadata_attribute(ase_file.graph, node.node_id, semantic_attribute(type_name, value))
                )
            else:
                raise ValueError(f"property {node.raw_fields[7]} field {key!r} must be string or null")
        if "enabled_if" in entry:
            condition = entry["enabled_if"]
            if condition is None:
                changes.append(
                    remove_property_metadata_attribute(
                        ase_file.graph, node.node_id, "EnableIfMzgui"
                    )
                )
            else:
                validated = validate_enable_if(condition)
                changes.append(
                    set_property_metadata_attribute(
                        ase_file.graph,
                        node.node_id,
                        enable_if_attribute(
                            validated["property"],
                            validated["operator"],
                            validated["value"],
                        ),
                    )
                )
    return changes


def _reorder_properties(graph: AseGraph, requested: list[NodeLine]) -> list[dict]:
    all_nodes = material_property_nodes(graph)
    requested_ids = {node.node_id for node in requested}
    instruction_order = {node.node_id: index for index, node in enumerate(all_nodes)}

    def current_order(node: NodeLine) -> tuple[int, int]:
        try:
            value = int(node.raw_fields[9])
        except (IndexError, ValueError):
            value = 2**31 - 1
        return value, instruction_order[node.node_id]

    remaining = sorted((node for node in all_nodes if node.node_id not in requested_ids), key=current_order)
    changes = []
    for order, node in enumerate([*requested, *remaining]):
        before = node.raw_fields[9]
        after = str(order)
        if before == after:
            continue
        node.raw_fields[9] = after
        graph.replace_node(node)
        changes.append(
            {
                "kind": "property_order",
                "node_id": node.node_id,
                "property_name": node.raw_fields[7],
                "before": before,
                "after": after,
            }
        )
    return changes
