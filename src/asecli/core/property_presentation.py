"""Machine-checkable presentation contract for ASECLI-managed properties."""

from __future__ import annotations

import re

from .compiled_properties import inspect_compiled_properties
from .custom_gui_versions import require_property_metadata_tail_version
from .model import AseFile


PROPERTY_PRESENTATION_CONTRACT = {
    "contract": "asecli.property-presentation.v1",
    "scope": "exported_properties",
    "display_name": {"language": "zh-Hans", "requires_han": True},
    "tooltip": {
        "providers": ["MZGUI.MZGUI", "ASECLI.MaterialGUI.ASECLIMaterialGUI"],
        "automatic_fields": ["property_name", "shader_default_value"],
        "property_name_format": "english_identifier",
    },
    "inline_help": {
        "attribute": "HelpBoxMzgui",
        "language": "zh-Hans",
        "requires_han": True,
        "presentation_contract": "asecli.inline-help.v1",
    },
}

_HAN = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]")
_ENGLISH_PROPERTY_NAME = re.compile(r"^_[A-Za-z][A-Za-z0-9_]*$")


def contains_han(text: object) -> bool:
    return isinstance(text, str) and bool(_HAN.search(text))


def set_property_display_name(ase_file: AseFile, node_id: str, display_name: str) -> dict:
    """Set the graph and compiled ShaderLab display name as one semantic change."""
    if not isinstance(display_name, str) or not display_name.strip() or len(display_name) > 128:
        raise ValueError("property display_name must be a non-empty string of at most 128 characters")
    if any(char in display_name for char in ('"', "'", ";", "\\", "\r", "\n")):
        raise ValueError("property display_name contains a forbidden quote, separator, escape, or newline")
    if not contains_han(display_name):
        raise ValueError("property display_name must contain Chinese characters")
    require_property_metadata_tail_version(ase_file.graph)
    node = ase_file.graph.node_by_id(node_id)
    if node is None:
        raise KeyError(f"node {node_id} not found")
    if len(node.raw_fields) <= 8 or node.raw_fields[6] != "Property":
        raise ValueError(f"node {node_id} is not an exported PropertyNode with a display name")

    property_name = node.raw_fields[7]
    pattern = re.compile(
        rf'(?m)^(?P<head>[ \t]*(?:\[[^\]\r\n]*\][ \t]*)*{re.escape(property_name)}[ \t]*\([ \t]*")'
        r'(?P<label>[^"\r\n]*)(?P<tail>"[ \t]*,)'
    )
    matches = list(pattern.finditer(ase_file.prefix))
    if len(matches) != 1:
        raise ValueError(
            f"expected one compiled ShaderLab declaration for {property_name!r}, found {len(matches)}"
        )
    match = matches[0]
    before_graph = node.raw_fields[8]
    before_compiled = match.group("label")
    node.raw_fields[8] = display_name
    ase_file.graph.replace_node(node)
    ase_file.prefix = (
        ase_file.prefix[: match.start("label")]
        + display_name
        + ase_file.prefix[match.end("label") :]
    )
    return {
        "kind": "property_display_name",
        "node_id": node_id,
        "property_name": property_name,
        "before": {"graph": before_graph, "compiled": before_compiled},
        "after": display_name,
    }


def inspect_property_presentation(
    editor: dict,
    properties: list[dict],
    compiled_source: str,
    *,
    supported_editors: frozenset[str],
) -> dict:
    """Inspect already-parsed Custom GUI state without importing graph modules."""
    claimed = (
        editor.get("graph") in supported_editors
        or editor.get("compiled") in supported_editors
    )
    managed = (
        editor.get("graph") in supported_editors
        and editor.get("compiled") == editor.get("graph")
        and editor.get("consistent") is True
    )
    violations: list[str] = []
    if not managed:
        violations.append("editor:mzgui_compatible_material_gui_required")

    compiled_properties, compiled_properties_error = inspect_compiled_properties(compiled_source)
    if compiled_properties_error is not None:
        violations.append("inspection:compiled_properties_unavailable")

    graph_by_name = _unique_properties(properties, "graph", violations)
    compiled_by_name = _unique_properties(compiled_properties, "compiled", violations)
    graph_names = set(graph_by_name)
    compiled_names = set(compiled_by_name)
    visible_compiled_names = {
        name for name, prop in compiled_by_name.items() if not prop.get("hidden", False)
    }
    graph_only = sorted(graph_names - compiled_names) if compiled_properties_error is None else []
    compiled_only = sorted(visible_compiled_names - graph_names) if compiled_properties_error is None else []
    violations.extend(f"property:{name}:compiled_property_required" for name in graph_only)
    violations.extend(f"compiled_property:{name}:graph_property_required" for name in compiled_only)

    property_results = []
    for prop in properties:
        property_name = prop.get("property_name")
        property_violations = []
        if not isinstance(property_name, str) or not _ENGLISH_PROPERTY_NAME.fullmatch(property_name):
            property_violations.append("property_name:english_identifier_required")
        if not contains_han(prop.get("display_name")):
            property_violations.append("display_name:chinese_required")
        help_values = [
            item.get("text")
            for item in prop.get("attributes", [])
            if item.get("type") in {"HelpBoxMzgui", "ASECLIHelpBox"}
        ]
        if len(help_values) != 1 or not contains_han(help_values[0]):
            property_violations.append("help:chinese_required")

        compiled = compiled_by_name.get(property_name)
        if compiled is not None:
            compiled_display_name = compiled.get("display_name")
            if not contains_han(compiled_display_name):
                property_violations.append("compiled_display_name:chinese_required")
            if compiled_display_name != prop.get("display_name"):
                property_violations.append("display_name:graph_compiled_mismatch")
            compiled_help_values = [
                item.get("text")
                for item in compiled.get("attributes", [])
                if item.get("type") in {"HelpBoxMzgui", "ASECLIHelpBox"}
            ]
            if len(compiled_help_values) != 1 or not contains_han(compiled_help_values[0]):
                property_violations.append("compiled_help:chinese_required")
            if help_values != compiled_help_values:
                property_violations.append("help:graph_compiled_mismatch")

        label = property_name if isinstance(property_name, str) else str(prop.get("node_id"))
        violations.extend(f"property:{label}:{item}" for item in property_violations)
        property_results.append(
            {
                "node_id": prop.get("node_id"),
                "property_name": property_name,
                "display_name": prop.get("display_name"),
                "compiled_display_name": compiled.get("display_name") if compiled else None,
                "valid": not property_violations,
                "violations": property_violations,
            }
        )

    return {
        **PROPERTY_PRESENTATION_CONTRACT,
        "claimed": claimed,
        "managed": managed,
        "inspection": "error" if compiled_properties_error is not None else "complete",
        "inspection_error": compiled_properties_error,
        "valid": managed and not violations,
        "violations": violations,
        "properties": property_results,
        "graph_properties": sorted(graph_names),
        "compiled_properties": sorted(compiled_names),
        "reconciliation": {
            "matched": sorted(graph_names & compiled_names),
            "graph_only": graph_only,
            "compiled_only": compiled_only,
        },
    }


def require_managed_property_presentation(ase_file: AseFile) -> dict | None:
    """Fail closed only after a file claims an MZGUI-compatible material GUI."""
    from .custom_gui import inspect_custom_gui

    try:
        result = inspect_custom_gui(ase_file)["property_presentation"]
    except ValueError as exc:
        if not _has_asecli_presentation_marker(ase_file):
            return None
        raise ValueError(
            f"MZGUI-compatible property presentation inspection failed: {exc}"
        ) from exc
    if result["valid"]:
        return result
    if not result["claimed"] and not _has_asecli_presentation_marker(ase_file):
        return result
    raise ValueError(
        "MZGUI-compatible property presentation contract failed: "
        + ", ".join(result["violations"])
    )


def require_property_presentation(ase_file: AseFile) -> dict:
    """Require the complete contract for a newly constructed ASE shader."""
    from .custom_gui import inspect_custom_gui

    result = inspect_custom_gui(ase_file)["property_presentation"]
    if result["valid"]:
        return result
    raise ValueError(
        "ASE property presentation contract failed: " + ", ".join(result["violations"])
    )


def _unique_properties(properties: list[dict], source: str, violations: list[str]) -> dict[str, dict]:
    result: dict[str, dict] = {}
    for prop in properties:
        name = prop.get("property_name")
        if not isinstance(name, str):
            violations.append(f"{source}_property:unknown:property_name_required")
            continue
        if name in result:
            violations.append(f"{source}_property:{name}:duplicate")
            continue
        result[name] = prop
    return result


def _has_asecli_presentation_marker(ase_file: AseFile) -> bool:
    text = ase_file.serialize()
    return any(editor in text for editor in PROPERTY_PRESENTATION_CONTRACT["tooltip"]["providers"]) or "Mzgui" in text or "[ASECLI" in text
