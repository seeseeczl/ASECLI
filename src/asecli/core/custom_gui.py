"""CustomEditor and ASECLI property-metadata support."""
from __future__ import annotations
from dataclasses import dataclass
import re
from .model import AseFile, AseGraph, NodeLine
from .custom_gui_versions import CUSTOM_EDITOR_GRAPH_VERSIONS, PROPERTY_METADATA_TAIL_GRAPH_VERSIONS, TARGET_ASE_VERSION, TARGET_GRAPH_VERSION, require_custom_editor_version, require_property_metadata_tail_version
from .material_gui_protocol import LEGACY_PROPERTY_METADATA_ATTRIBUTE_TYPES as _ALTERNATE_ASECLI_ATTRIBUTE_TYPES, MANAGED_PROPERTY_METADATA_ATTRIBUTE_TYPES, PROPERTY_METADATA_ATTRIBUTE_TYPES, canonical_property_metadata_type, equivalent_property_metadata_types
from .material_gui_condition import parse_enable_if_arguments
from .property_presentation import inspect_property_presentation

ASECLI_GUI_EDITOR = "ASECLI.MaterialGUI.ASECLIMaterialGUI"
MZGUI_EDITOR = "MZGUI.MZGUI"
SUPPORTED_GUI_EDITORS = frozenset((MZGUI_EDITOR, ASECLI_GUI_EDITOR))
CUSTOM_EDITOR_SUGGESTIONS = ("ASEMaterialInspector", MZGUI_EDITOR, ASECLI_GUI_EDITOR, "Rendering.HighDefinition.LightingShaderGraphGUI", "Rendering.HighDefinition.HDUnlitGUI", "UnityEditor.Rendering.HighDefinition.HDLitGUI", "UnityEditor.ShaderGraph.PBRMasterGUI", "UnityEditor.Rendering.HighDefinition.DecalGUI", "UnityEditor.Rendering.HighDefinition.FabricGUI", "UnityEditor.Experimental.Rendering.HDPipeline.HDLitGUI", "Rendering.HighDefinition.DecalGUI", "Rendering.HighDefinition.LitShaderGraphGUI", "Rendering.HighDefinition.DecalShaderGraphGUI", "UnityEditor.ShaderGraphUnlitGUI", "UnityEditor.ShaderGraphLitGUI", "UnityEditor.Rendering.Universal.DecalShaderGraphGUI")
_MASTER_TYPES = {"AmplifyShaderEditor.TemplateMultiPassMasterNode", "AmplifyShaderEditor.TemplateMasterNode", "AmplifyShaderEditor.StandardSurfaceOutputNode", "AmplifyShaderEditor.LogNode"}
_EDITOR_CLASS_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)*$")
_ATTRIBUTE_RE = re.compile(r"^\[(?P<type>[A-Za-z_][A-Za-z0-9_]*)(?:\((?P<args>.*)\))?\]$")
_CUSTOM_EDITOR_LINE_RE = re.compile(r'(?m)^(?P<indent>[ \t]*)CustomEditor[ \t]+"(?P<name>[^"\r\n]*)"[ \t]*(?:\r?\n|$)')
_FALLBACK_LINE_RE = re.compile(r"(?im)^(?P<indent>[ \t]*)fallback\b")
_GROUP_INVALID = frozenset("\r\n\\><'\";:[]{}=+`~/?!@#$%^&*")
@dataclass(frozen=True)
class PropertyMetadataTail:
    count_index: int; attributes: tuple[str, ...]
def validate_editor_class(name: str) -> str:
    if len(name) > 255 or not _EDITOR_CLASS_RE.fullmatch(name):
        raise ValueError(
            "custom editor must be a namespace-qualified C# class name using only letters, digits, '_' and '.'"
        )
    return name
def main_master_node(graph: AseGraph) -> NodeLine:
    require_custom_editor_version(graph)
    candidates = [node for node in graph.nodes if node.type_name in _MASTER_TYPES
                  and len(node.raw_fields) > 9 and node.raw_fields[6].lower() == "true"]
    if len(candidates) != 1:
        raise ValueError(f"expected exactly one main MasterNode, found {len(candidates)}")
    return candidates[0]
def graph_custom_editor(graph: AseGraph) -> str | None:
    value = main_master_node(graph).raw_fields[9]
    return value or None
def compiled_custom_editor(ase_file: AseFile) -> str | None:
    matches = list(_CUSTOM_EDITOR_LINE_RE.finditer(ase_file.prefix))
    if len(matches) > 1:
        raise ValueError(f"expected at most one compiled CustomEditor directive, found {len(matches)}")
    return matches[0].group("name") if matches else None
def set_custom_editor(ase_file: AseFile, editor: str | None) -> dict:
    if editor is not None:
        validate_editor_class(editor)
        editor = MZGUI_EDITOR if editor == ASECLI_GUI_EDITOR else editor
    node = main_master_node(ase_file.graph)
    before_graph = node.raw_fields[9] or None
    before_compiled = compiled_custom_editor(ase_file)
    node.raw_fields[9] = editor or ""
    ase_file.graph.replace_node(node)
    ase_file.prefix = _replace_compiled_editor(ase_file.prefix, editor)
    return {"kind": "custom_editor", "main_node_id": node.node_id,
            "before": {"graph": before_graph, "compiled": before_compiled}, "after": editor}
def _replace_compiled_editor(prefix: str, editor: str | None) -> str:
    matches = list(_CUSTOM_EDITOR_LINE_RE.finditer(prefix))
    if len(matches) > 1:
        raise ValueError(f"expected at most one compiled CustomEditor directive, found {len(matches)}")
    if matches:
        match = matches[0]
        if editor is None:
            return prefix[: match.start()] + prefix[match.end() :]
        raw = match.group(0)
        eol = "\r\n" if raw.endswith("\r\n") else ("\n" if raw.endswith("\n") else "")
        line = f'{match.group("indent")}CustomEditor "{editor}"{eol}'
        return prefix[: match.start()] + line + prefix[match.end() :]
    if editor is None:
        return prefix
    eol = "\r\n" if "\r\n" in prefix else "\n"
    fallback = _FALLBACK_LINE_RE.search(prefix)
    if fallback:
        line = f'{fallback.group("indent")}CustomEditor "{editor}"{eol}'
        return prefix[: fallback.start()] + line + prefix[fallback.start() :]
    closing_braces = list(re.finditer(r"(?m)^[ \t]*}[ \t]*(?:\r?\n|$)", prefix))
    if not closing_braces:
        raise ValueError("cannot insert compiled CustomEditor: ShaderLab closing brace not found")
    insert_at = closing_braces[-1].start()
    return prefix[:insert_at] + f'\tCustomEditor "{editor}"{eol}' + prefix[insert_at:]
def encode_custom_unicode(text: str) -> str:
    raw = text.encode("utf-16-le", errors="surrogatepass")
    return "".join(f"#{int.from_bytes(raw[i:i + 2], 'little'):04X}" for i in range(0, len(raw), 2))
def decode_custom_unicode(value: str) -> str:
    units = re.findall(r"#([0-9A-Fa-f]{4})", value)
    raw = b"".join(int(unit, 16).to_bytes(2, "little") for unit in units)
    return raw.decode("utf-16-le", errors="replace")
def encode_foldout_title(text: str) -> str:
    invalid = sorted({char for char in text if char in _GROUP_INVALID})
    if invalid:
        rendered = " ".join(repr(char) for char in invalid)
        raise ValueError(f"group title contains characters rejected by ASE: {rendered}")
    raw = text.encode("utf-16-le", errors="surrogatepass")
    values = [int.from_bytes(raw[i:i + 2], "little") for i in range(0, len(raw), 2)]
    return "".join(chr(value) if value <= 127 else f"#{value:04x}" for value in values)
def decode_foldout_title(value: str) -> str:
    def replace(match: re.Match[str]) -> str:
        return chr(int(match.group(1), 16))
    decoded = re.sub(r"#([0-9A-Fa-f]{4})", replace, value)
    return decoded.encode("utf-16-le", errors="surrogatepass").decode("utf-16-le", errors="replace")
def is_material_property_node(node: NodeLine) -> bool:
    return len(node.raw_fields) > 7 and node.raw_fields[6] == "Property"
def parse_property_metadata_attribute(raw: str) -> dict:
    match = _ATTRIBUTE_RE.fullmatch(raw)
    if not match:
        raise ValueError(f"invalid property metadata serialization: {raw!r}")
    type_name = match.group("type")
    args = match.group("args")
    result = {"type": type_name, "raw": raw, "args": args}
    if args is not None and type_name in {"ASECLITooltip", "ASECLIHelpBox", "TooltipMzgui", "HelpBoxMzgui"}:
        result["text"] = decode_custom_unicode(args)
    elif args is not None and type_name in {"ASECLIEnableIf", "EnableIfMzgui"}:
        result["condition"] = parse_enable_if_arguments(args)
    elif args is not None and type_name in {"ASECLIFoldout", "FoldoutMzgui"}:
        result["text"] = decode_foldout_title(args)
    return result
def read_property_metadata_tail(graph: AseGraph, node: NodeLine) -> PropertyMetadataTail:
    require_property_metadata_tail_version(graph)
    if not is_material_property_node(node):
        raise ValueError(f"node {node.node_id} is not an exported PropertyNode")
    fields = node.raw_fields
    for index in range(len(fields) - 1, 5, -1):
        value = fields[index]
        if not value.isdigit():
            continue
        count = int(value)
        if count != len(fields) - index - 1:
            continue
        attributes = fields[index + 1 :]
        try:
            for attribute in attributes:
                parse_property_metadata_attribute(attribute)
        except ValueError:
            continue
        return PropertyMetadataTail(index, tuple(attributes))
    raise ValueError(f"node {node.node_id} has no valid property metadata serialization tail")
def _validated_raw_attribute(raw: str) -> tuple[str, str]:
    if any(char in raw for char in (";", "\r", "\n", "\"", "'", "\\")):
        raise ValueError("raw property metadata attribute contains a forbidden serialization character")
    parsed = parse_property_metadata_attribute(raw)
    type_name = str(parsed["type"])
    canonical_type = canonical_property_metadata_type(type_name)
    if canonical_type is None:
        raise ValueError(
            "unsupported MZGUI-compatible property metadata attribute type: " + type_name
        )
    return canonical_type, raw
def set_property_metadata_attribute(graph: AseGraph, node_id: str, raw: str) -> dict:
    type_name, raw = _validated_raw_attribute(raw)
    node = graph.node_by_id(node_id)
    if node is None:
        raise KeyError(f"node {node_id} not found")
    tail = read_property_metadata_tail(graph, node)
    attributes = list(tail.attributes)
    matching = [
        index
        for index, item in enumerate(attributes)
        if parse_property_metadata_attribute(item)["type"]
        in equivalent_property_metadata_types(type_name)
    ]
    before = [attributes[i] for i in matching]
    if matching:
        first = matching[0]
        attributes[first] = raw
        for index in reversed(matching[1:]):
            del attributes[index]
    else:
        attributes.append(raw)
    _write_property_metadata_tail(graph, node, tail.count_index, attributes)
    return {"kind": "property_metadata", "node_id": node_id, "type": type_name, "before": before, "after": raw}
def remove_property_metadata_attribute(graph: AseGraph, node_id: str, type_name: str) -> dict:
    canonical_type = canonical_property_metadata_type(type_name)
    if canonical_type is None:
        raise ValueError(f"unsupported MZGUI-compatible property metadata attribute type: {type_name}")
    node = graph.node_by_id(node_id)
    if node is None:
        raise KeyError(f"node {node_id} not found")
    tail = read_property_metadata_tail(graph, node)
    types = equivalent_property_metadata_types(canonical_type)
    removed = [item for item in tail.attributes if parse_property_metadata_attribute(item)["type"] in types]
    kept = [item for item in tail.attributes if parse_property_metadata_attribute(item)["type"] not in types]
    _write_property_metadata_tail(graph, node, tail.count_index, kept)
    return {"kind": "property_metadata", "node_id": node_id, "type": canonical_type, "removed": removed}
def _write_property_metadata_tail(graph: AseGraph, node: NodeLine, count_index: int, attributes: list[str]) -> None:
    node.raw_fields = node.raw_fields[:count_index] + [str(len(attributes)), *attributes]
    graph.replace_node(node)
def semantic_attribute(type_name: str, text: str) -> str:
    if len(text) > 4096:
        raise ValueError("custom GUI text must not exceed 4096 characters")
    canonical_type = canonical_property_metadata_type(type_name)
    if canonical_type is None:
        raise ValueError(f"no text semantic encoder for {type_name}")
    if canonical_type == "FoldoutMzgui":
        encoded = encode_foldout_title(text)
    elif canonical_type in {"TooltipMzgui", "HelpBoxMzgui"}:
        encoded = encode_custom_unicode(text)
    else:
        raise ValueError(f"no text semantic encoder for {type_name}")
    return f"[{type_name}({encoded})]"
def inspect_custom_gui(ase_file: AseFile) -> dict:
    main = main_master_node(ase_file.graph)
    graph_editor = main.raw_fields[9] or None
    compiled_editor = compiled_custom_editor(ase_file)
    properties = []
    property_metadata_tail_supported = ase_file.graph.version in PROPERTY_METADATA_TAIL_GRAPH_VERSIONS
    if property_metadata_tail_supported:
        for node in ase_file.graph.nodes:
            if not is_material_property_node(node):
                continue
            tail = read_property_metadata_tail(ase_file.graph, node)
            properties.append(
                {
                    "node_id": node.node_id,
                    "node_type": node.type_name,
                    "property_name": node.raw_fields[7] if len(node.raw_fields) > 7 else None, "order_index": int(node.raw_fields[9]),
                    "display_name": node.raw_fields[8] if len(node.raw_fields) > 8 else None,
                    "attributes": [parse_property_metadata_attribute(raw) for raw in tail.attributes],
                }
            )
    editor = {"main_node_id": main.node_id, "graph": graph_editor,
              "compiled": compiled_editor, "consistent": graph_editor == compiled_editor}
    return {
        "ase_profile": TARGET_ASE_VERSION,
        "version_capabilities": {
            "custom_editor": ase_file.graph.version in CUSTOM_EDITOR_GRAPH_VERSIONS,
            "property_metadata_tail": property_metadata_tail_supported,
        },
        "profile_graph_version": TARGET_GRAPH_VERSION,
        "graph_version": ase_file.graph.version,
        "editor": editor,
        "properties": properties,
        "property_presentation": inspect_property_presentation(
            editor, properties, ase_file.prefix, supported_editors=SUPPORTED_GUI_EDITORS
        ),
        "capabilities": {
            "supported_editors": sorted(SUPPORTED_GUI_EDITORS),
            "built_in_editor": MZGUI_EDITOR,
            "legacy_fallback_editor": ASECLI_GUI_EDITOR,
            "editor_suggestions": list(CUSTOM_EDITOR_SUGGESTIONS),
            "property_attribute_types": list(PROPERTY_METADATA_ATTRIBUTE_TYPES),
            "legacy_read_attribute_types": list(_ALTERNATE_ASECLI_ATTRIBUTE_TYPES),
            "semantic_operations": {
                "group": "FoldoutMzgui",
                "tooltip": "TooltipMzgui",
                "help_box": "HelpBoxMzgui",
                "enabled_if": "EnableIfMzgui",
            },
            "shader_drawer_only": ["ShowIf"],
        },
    }
