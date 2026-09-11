"""Fail-closed ShaderLab, grouping, and texture evidence reconciliation."""

from __future__ import annotations

from ..core import inspect_comment_groups
from .model import diagnostic
from .sources import sampler_texture_guid, texture_dependency


_TEMPLATE_PROPERTIES = {
    "_AlphaCutoff": ("float", False, {"Range(0, 1)"}),
    "_EmissionColor": ("color", False, {"Color"}),
    "_QueueControl": ("float", False, {"Float"}),
    "_QueueOffset": ("float", False, {"Float"}),
    "_ReceiveShadows": ("float", False, {"Float"}),
    "_texcoord": ("texture2d", False, {"2D"}),
    "unity_Lightmaps": ("unsupported", False, {"2DArray"}),
    "unity_LightmapsInd": ("unsupported", False, {"2DArray"}),
    "unity_ShadowMasks": ("unsupported", False, {"2DArray"}),
}


def reconcile_shaderlab_properties(compiled, properties, report, diagnostics):
    mapped = {row["name"] for row in properties}
    for name, row in sorted(compiled.items()):
        if name in mapped:
            continue
        expected = _TEMPLATE_PROPERTIES.get(name)
        if (expected and row["type"] == expected[0] and row["exposed"] is expected[1]
                and row.get("shaderlab_type") in expected[2]):
            kind = "engine_managed_property" if name.startswith("unity_") else "template_managed_property"
            report["mappings"].append({
                "source_nodes": [], "target_nodes": ["URP.UnlitTarget"],
                "kind": kind, "property": name, "ports": [],
            })
            continue
        diagnostics.append(diagnostic(None, "SHADERLAB_PROPERTY_UNMAPPED", {
            "property": name, "type": row.get("shaderlab_type"), "exposed": row.get("exposed"),
        }, "A ShaderLab property or external Inspector consumer would be lost"))


def verify_texture_dependencies(ase, source, target, properties, nodes, report, diagnostics):
    by_name = {
        node.raw_fields[7]: node for node in ase.graph.nodes
        if node.type_name == "AmplifyShaderEditor.SamplerNode" and len(node.raw_fields) > 20
    }
    dependencies = []
    semantic_by_source = {}
    for item in nodes:
        semantic_by_source.setdefault(item.source_id, []).append(item)
    for prop in properties:
        if prop["type"] != "texture2d":
            continue
        if prop.get("default") is None:
            dependencies.append({"property": prop["name"], "asset": None, "status": "explicit_null"})
            continue
        source_node = by_name.get(prop["name"])
        try:
            guid = sampler_texture_guid(source_node) if source_node else ""
        except ValueError as exc:
            diagnostics.append(diagnostic(source_node.node_id if source_node else None,
                "TEXTURE_IMPORTER_UNVERIFIED", str(exc),
                "Texture type, color space, sampling, or compression equivalence is not proven"))
            continue
        try:
            evidence, texture_type = texture_dependency(source, target, guid, prop["default"])
        except (OSError, ValueError) as exc:
            diagnostics.append(diagnostic(source_node.node_id if source_node else None,
                "TEXTURE_IMPORTER_UNVERIFIED", str(exc),
                "Texture type, color space, sampling, or compression equivalence is not proven"))
            continue
        evidence["property"] = prop["name"]
        dependencies.append(evidence)
        for item in semantic_by_source.get(source_node.node_id, []):
            if item.target_type == "sample-texture":
                item.settings["textureType"] = texture_type
    report["dependencies"] = dependencies


def groups(ase, mappings, diagnostics):
    try:
        rows = inspect_comment_groups(ase.graph)
    except ValueError as exc:
        diagnostics.append(diagnostic(None, "COMMENT_INVALID", str(exc),
                                      "Comment grouping cannot be preserved"))
        return []
    by_id = {row["node_id"]: row for row in rows}
    result = []
    for row in rows:
        try:
            members = _leaf_members(row["node_id"], by_id, set())
        except ValueError as exc:
            diagnostics.append(diagnostic(row["node_id"], "COMMENT_INVALID", str(exc),
                                          "Comment grouping cannot be preserved"))
            continue
        targets = [end[0] for member in members for key, end in mappings.get(member, {}).items() if key >= 0]
        targets = list(dict.fromkeys(targets))
        if targets:
            result.append({"title": row["title"] or row["note"] or "Comment", "nodes": targets})
    return result


def unique_properties(rows, diagnostics):
    result = {}
    for row in rows:
        if row["name"] in result and result[row["name"]] != row:
            diagnostics.append(diagnostic(None, "PROPERTY_CONFLICT", row["name"],
                                          "Property definitions disagree"))
        result[row["name"]] = row
    return list(result.values())


def _leaf_members(group_id, groups_by_id, seen):
    if group_id in seen:
        raise ValueError(f"nested Comment cycle at {group_id}")
    seen = seen | {group_id}
    result = []
    for member in groups_by_id[group_id]["members"]:
        result.extend(_leaf_members(member, groups_by_id, seen) if member in groups_by_id else [member])
    return result
