"""Preserve ASECLI property metadata across real ASE recompilation."""

from __future__ import annotations

import os

from ..core import (
    AseFile,
    graph_custom_editor,
    inspect_custom_gui,
    MANAGED_PROPERTY_METADATA_ATTRIBUTE_TYPES,
    resolve_property_node,
    set_custom_editor,
    set_property_metadata_attribute,
    sync_compiled_property_metadata,
)


def snapshot_recompile_metadata(path: str) -> dict | None:
    if not os.path.isfile(path):
        return None
    try:
        ase_file = AseFile.from_path(path)
        state = inspect_custom_gui(ase_file)
    except (OSError, ValueError):
        return None
    properties = []
    for prop in state["properties"]:
        attributes = [
            item["raw"] for item in prop["attributes"]
            if item["type"] in MANAGED_PROPERTY_METADATA_ATTRIBUTE_TYPES
        ]
        if attributes:
            properties.append({"name": prop["property_name"], "attributes": attributes})
    editor = graph_custom_editor(ase_file.graph)
    if not properties and editor is None:
        return None
    return {"editor": editor, "properties": properties}


def restore_recompile_metadata(path: str, snapshot: dict) -> tuple[AseFile, int]:
    ase_file = AseFile.from_path(path)
    editor = snapshot.get("editor")
    if editor:
        set_custom_editor(ase_file, editor)
    restored = 0
    for prop in snapshot["properties"]:
        node = resolve_property_node(ase_file.graph, property_name=prop["name"])
        for raw in prop["attributes"]:
            set_property_metadata_attribute(ase_file.graph, node.node_id, raw)
            restored += 1
    sync_compiled_property_metadata(ase_file)
    return ase_file, restored
