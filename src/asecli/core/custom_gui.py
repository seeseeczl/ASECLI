"""CustomEditor and MZGUI-compatible metadata support."""
from __future__ import annotations
from dataclasses import dataclass
import re
from .model import AseFile, AseGraph, NodeLine
TARGET_ASE_VERSION = "1.9.6.2"
TARGET_GRAPH_VERSION = "19602"
MZGUI_EDITOR = "MZGUI.MZGUI"
ASECLI_GUI_EDITOR = "ASECLI.MaterialGUI.ASECLIMaterialGUI"
SUPPORTED_GUI_EDITORS = frozenset((MZGUI_EDITOR, ASECLI_GUI_EDITOR))
CUSTOM_EDITOR_SUGGESTIONS = ("ASEMaterialInspector", MZGUI_EDITOR, ASECLI_GUI_EDITOR, "Rendering.HighDefinition.LightingShaderGraphGUI", "Rendering.HighDefinition.HDUnlitGUI", "UnityEditor.Rendering.HighDefinition.HDLitGUI",
                             "UnityEditor.ShaderGraph.PBRMasterGUI", "UnityEditor.Rendering.HighDefinition.DecalGUI", "UnityEditor.Rendering.HighDefinition.FabricGUI", "UnityEditor.Experimental.Rendering.HDPipeline.HDLitGUI",
                             "Rendering.HighDefinition.DecalGUI", "Rendering.HighDefinition.LitShaderGraphGUI", "Rendering.HighDefinition.DecalShaderGraphGUI", "UnityEditor.ShaderGraphUnlitGUI", "UnityEditor.ShaderGraphLitGUI", "UnityEditor.Rendering.Universal.DecalShaderGraphGUI")
MZGUI_ATTRIBUTE_TYPES = ("FoldoutMzgui", "RampMzgui", "TextureMzgui", "VectorMzgui",
                          "HelpBoxMzgui", "TooltipMzgui", "KeywordDescMzgui")
_MASTER_TYPES = {
    "AmplifyShaderEditor.TemplateMultiPassMasterNode",
    "AmplifyShaderEditor.TemplateMasterNode",
    "AmplifyShaderEditor.StandardSurfaceOutputNode",
    "AmplifyShaderEditor.LogNode",
}
_EDITOR_CLASS_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)*$")
_ATTRIBUTE_RE = re.compile(
    r"^\[(?P<type>[A-Za-z_][A-Za-z0-9_]*)(?:\((?P<args>.*)\))?\]$"
)
_CUSTOM_EDITOR_LINE_RE = re.compile(
    r'(?m)^(?P<indent>[ \t]*)CustomEditor[ \t]+"(?P<name>[^"\r\n]*)"[ \t]*(?:\r?\n|$)'
)
_FALLBACK_LINE_RE = re.compile(r"(?im)^(?P<indent>[ \t]*)fallback\b")
_GROUP_INVALID = frozenset("\r\n\\><'\";:[]{}=+`~/?!@#$%^&*")
@dataclass(frozen=True)
class MzguiTail:
    count_index: int
    attributes: tuple[str, ...]
def _numeric_version(graph: AseGraph) -> int:
    try:
        return int(graph.version)
    except ValueError as exc:
        raise ValueError(f"unsupported non-numeric ASE graph version: {graph.version!r}") from exc
def validate_editor_class(name: str) -> str:
    if len(name) > 255 or not _EDITOR_CLASS_RE.fullmatch(name):
        raise ValueError(
            "custom editor must be a namespace-qualified C# class name using only letters, digits, '_' and '.'"
        )
    return name
def main_master_node(graph: AseGraph) -> NodeLine:
    if _numeric_version(graph) <= 2404:
        raise ValueError(f"graph version {graph.version} predates serialized CustomEditor support")
    candidates = [
        node
        for node in graph.nodes
        if node.type_name in _MASTER_TYPES
        and len(node.raw_fields) > 9
        and node.raw_fields[6].lower() == "true"
    ]
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
    node = main_master_node(ase_file.graph)
    before_graph = node.raw_fields[9] or None
    before_compiled = compiled_custom_editor(ase_file)
    node.raw_fields[9] = editor or ""
    ase_file.graph.replace_node(node)
    ase_file.prefix = _replace_compiled_editor(ase_file.prefix, editor)
    return {
        "kind": "custom_editor",
        "main_node_id": node.node_id,
        "before": {"graph": before_graph, "compiled": before_compiled},
        "after": editor,
    }
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
def parse_mzgui_attribute(raw: str) -> dict:
    match = _ATTRIBUTE_RE.fullmatch(raw)
    if not match:
        raise ValueError(f"invalid MZGUI attribute serialization: {raw!r}")
    type_name = match.group("type")
    args = match.group("args")
    result = {"type": type_name, "raw": raw, "args": args}
    if args is not None and type_name in {"TooltipMzgui", "HelpBoxMzgui"}:
        result["text"] = decode_custom_unicode(args)
    elif args is not None and type_name == "FoldoutMzgui":
        result["text"] = decode_foldout_title(args)
    return result
def read_mzgui_tail(graph: AseGraph, node: NodeLine) -> MzguiTail:
    if _numeric_version(graph) <= 4102:
        raise ValueError(f"graph version {graph.version} predates MZGUI tail serialization")
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
                parse_mzgui_attribute(attribute)
        except ValueError:
            continue
        return MzguiTail(index, tuple(attributes))
    raise ValueError(f"node {node.node_id} has no valid MZGUI serialization tail")
def _validated_raw_attribute(raw: str) -> tuple[str, str]:
    if any(char in raw for char in (";", "\r", "\n", "\"", "'", "\\")):
        raise ValueError("raw MZGUI attribute contains a forbidden serialization character")
    parsed = parse_mzgui_attribute(raw)
    type_name = str(parsed["type"])
    if type_name not in MZGUI_ATTRIBUTE_TYPES:
        raise ValueError(f"unsupported PropertyNode MZGUI attribute type: {type_name}")
    return type_name, raw
def set_mzgui_attribute(graph: AseGraph, node_id: str, raw: str) -> dict:
    type_name, raw = _validated_raw_attribute(raw)
    node = graph.node_by_id(node_id)
    if node is None:
        raise KeyError(f"node {node_id} not found")
    tail = read_mzgui_tail(graph, node)
    attributes = list(tail.attributes)
    matching = [i for i, item in enumerate(attributes) if parse_mzgui_attribute(item)["type"] == type_name]
    before = [attributes[i] for i in matching]
    if matching:
        first = matching[0]
        attributes[first] = raw
        for index in reversed(matching[1:]):
            del attributes[index]
    else:
        attributes.append(raw)
    _write_mzgui_tail(graph, node, tail.count_index, attributes)
    return {"kind": "mzgui_attribute", "node_id": node_id, "type": type_name, "before": before, "after": raw}
def remove_mzgui_attribute(graph: AseGraph, node_id: str, type_name: str) -> dict:
    if type_name not in MZGUI_ATTRIBUTE_TYPES:
        raise ValueError(f"unsupported PropertyNode MZGUI attribute type: {type_name}")
    node = graph.node_by_id(node_id)
    if node is None:
        raise KeyError(f"node {node_id} not found")
    tail = read_mzgui_tail(graph, node)
    removed = [item for item in tail.attributes if parse_mzgui_attribute(item)["type"] == type_name]
    kept = [item for item in tail.attributes if parse_mzgui_attribute(item)["type"] != type_name]
    _write_mzgui_tail(graph, node, tail.count_index, kept)
    return {"kind": "mzgui_attribute", "node_id": node_id, "type": type_name, "removed": removed}
def _write_mzgui_tail(graph: AseGraph, node: NodeLine, count_index: int, attributes: list[str]) -> None:
    node.raw_fields = node.raw_fields[:count_index] + [str(len(attributes)), *attributes]
    graph.replace_node(node)
def semantic_attribute(type_name: str, text: str) -> str:
    if len(text) > 4096:
        raise ValueError("custom GUI text must not exceed 4096 characters")
    if type_name == "FoldoutMzgui":
        encoded = encode_foldout_title(text)
    elif type_name in {"TooltipMzgui", "HelpBoxMzgui"}:
        encoded = encode_custom_unicode(text)
    else:
        raise ValueError(f"no text semantic encoder for {type_name}")
    return f"[{type_name}({encoded})]"
def inspect_custom_gui(ase_file: AseFile) -> dict:
    main = main_master_node(ase_file.graph)
    graph_editor = main.raw_fields[9] or None
    compiled_editor = compiled_custom_editor(ase_file)
    properties = []
    for node in ase_file.graph.nodes:
        if not is_material_property_node(node):
            continue
        tail = read_mzgui_tail(ase_file.graph, node)
        properties.append(
            {
                "node_id": node.node_id,
                "node_type": node.type_name,
                "property_name": node.raw_fields[7] if len(node.raw_fields) > 7 else None, "order_index": int(node.raw_fields[9]),
                "display_name": node.raw_fields[8] if len(node.raw_fields) > 8 else None,
                "attributes": [parse_mzgui_attribute(raw) for raw in tail.attributes],
            }
        )
    return {
        "ase_profile": TARGET_ASE_VERSION,
        "profile_graph_version": TARGET_GRAPH_VERSION,
        "graph_version": ase_file.graph.version,
        "editor": {
            "main_node_id": main.node_id,
            "graph": graph_editor,
            "compiled": compiled_editor,
            "consistent": graph_editor == compiled_editor,
        },
        "properties": properties,
        "capabilities": {
            "supported_editors_for_mzgui": sorted(SUPPORTED_GUI_EDITORS),
            "built_in_compat_editor": ASECLI_GUI_EDITOR, "provider_selection_command": "asecli gui-support <unity-project-root>",
            "editor_suggestions": list(CUSTOM_EDITOR_SUGGESTIONS),
            "property_attribute_types": list(MZGUI_ATTRIBUTE_TYPES),
            "semantic_operations": {"group": "FoldoutMzgui", "tooltip": "TooltipMzgui", "help_box": "HelpBoxMzgui"},
            "shader_drawer_only": ["ShowIf"],
        },
    }
