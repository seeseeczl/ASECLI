"""Post-ASE synchronization for managed ShaderLab property metadata."""

from __future__ import annotations

import re

from .custom_gui import (
    MANAGED_PROPERTY_METADATA_ATTRIBUTE_TYPES,
    PROPERTY_METADATA_ATTRIBUTE_TYPES,
    is_material_property_node,
    parse_property_metadata_attribute,
    read_property_metadata_tail,
)
from .compiled_properties import inspect_compiled_properties
from .model import AseFile


_MANAGED_ATTRIBUTE_TYPES = frozenset(
    MANAGED_PROPERTY_METADATA_ATTRIBUTE_TYPES
)
_KNOWN_TEMPLATE_COMPILED_ONLY_PROPERTIES = {
    "2992e84f91cbeb14eab234972e07ea9d": frozenset({
        "_TessPhongStrength",
        "_TessValue",
        "_TessMin",
        "_TessMax",
        "_TessEdgeLength",
        "_TessMaxDisp",
    }),
}


def hide_known_template_compiled_only_properties(
    ase_file: AseFile, template_guid: str
) -> list[dict]:
    """Hide exact, versioned template controls that have no graph PropertyNode.

    Unknown compiled-only properties remain visible so the presentation
    contract can reject them instead of silently hiding user-owned data.
    """
    compiled, error = inspect_compiled_properties(ase_file.prefix)
    if error is not None:
        raise ValueError(f"compiled ShaderLab properties are unavailable: {error}")
    known = _KNOWN_TEMPLATE_COMPILED_ONLY_PROPERTIES.get(template_guid, frozenset())
    graph_names = {
        node.raw_fields[7]
        for node in ase_file.graph.nodes
        if is_material_property_node(node)
    }
    changes: list[dict] = []
    prefix = ase_file.prefix
    for prop in compiled:
        property_name = prop["property_name"]
        if prop["hidden"] or property_name in graph_names or property_name not in known:
            continue
        pattern = re.compile(
            rf"(?m)^(?P<indent>[ \t]*)(?P<attributes>(?:\[[^\]\r\n]*\][ \t]*)*)"
            rf"(?P<name>{re.escape(property_name)})(?P<suffix>[ \t]*\()"
        )
        matches = list(pattern.finditer(prefix))
        if len(matches) != 1:
            raise ValueError(
                f"expected one compiled ShaderLab declaration for {property_name!r}, found {len(matches)}"
            )
        match = matches[0]
        replacement = (
            match.group("indent")
            + "[HideInInspector] "
            + match.group("attributes")
            + match.group("name")
            + match.group("suffix")
        )
        prefix = prefix[: match.start()] + replacement + prefix[match.end() :]
        changes.append({
            "kind": "compiled_template_property_hidden",
            "property_name": property_name,
            "template_guid": template_guid,
        })
    ase_file.prefix = prefix
    return changes


def sync_compiled_property_metadata(ase_file: AseFile) -> list[dict]:
    """Mirror graph metadata into compiled properties after an ASE save.

    Some editor builds discard custom PropertyNode attributes while saving.
    Unity's ShaderGUI reads decorators from the compiled ``Properties`` block,
    so restore the managed attributes there while preserving unrelated ones.
    """
    changes: list[dict] = []
    prefix = ase_file.prefix
    for node in ase_file.graph.nodes:
        if not is_material_property_node(node):
            continue
        property_name = node.raw_fields[7]
        tail = read_property_metadata_tail(ase_file.graph, node)
        managed = [
            raw for raw in tail.attributes
            if parse_property_metadata_attribute(raw)["type"] in _MANAGED_ATTRIBUTE_TYPES
        ]
        pattern = re.compile(
            rf"(?m)^(?P<indent>[ \t]*)(?P<attributes>(?:\[[^\]\r\n]*\][ \t]*)*)"
            rf"(?P<name>{re.escape(property_name)})(?P<suffix>[ \t]*\()"
        )
        matches = list(pattern.finditer(prefix))
        if len(matches) != 1:
            raise ValueError(
                f"expected one compiled ShaderLab declaration for {property_name!r}, found {len(matches)}"
            )
        match = matches[0]
        existing = re.findall(r"\[[^\]\r\n]*\]", match.group("attributes"))
        preserved = [raw for raw in existing if not _is_managed(raw)]
        attributes = [*preserved, *managed]
        replacement = (
            match.group("indent")
            + ((" ".join(attributes) + " ") if attributes else "")
            + match.group("name")
            + match.group("suffix")
        )
        if match.group(0) == replacement:
            continue
        prefix = prefix[: match.start()] + replacement + prefix[match.end() :]
        changes.append({
            "kind": "compiled_property_metadata", "node_id": node.node_id,
            "property_name": property_name, "before": existing, "after": attributes,
        })
    ase_file.prefix = prefix
    return changes


def _is_managed(raw: str) -> bool:
    try:
        return parse_property_metadata_attribute(raw)["type"] in _MANAGED_ATTRIBUTE_TYPES
    except ValueError:
        return False
