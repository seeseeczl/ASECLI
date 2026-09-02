"""Post-ASE synchronization for managed ShaderLab property metadata."""

from __future__ import annotations

import re

from .custom_gui import (
    PROPERTY_METADATA_ATTRIBUTE_TYPES,
    is_material_property_node,
    parse_property_metadata_attribute,
    read_property_metadata_tail,
)
from .model import AseFile


_LEGACY_ATTRIBUTE_TYPES = ("FoldoutMzgui", "TooltipMzgui", "HelpBoxMzgui")
_MANAGED_ATTRIBUTE_TYPES = frozenset(
    (*PROPERTY_METADATA_ATTRIBUTE_TYPES, *_LEGACY_ATTRIBUTE_TYPES)
)


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
