"""Validation implementation split from the public EditorGraphSpec model."""

from __future__ import annotations

import math
import re
from typing import Any

from ._editor_port_contract import validate_connections
from .editor_spec import (
    ConnectionSpec,
    EditorGraphSpec,
    EndpointSpec,
    InputSpec,
    NodeSpec,
    SpecError,
    TemplateSpec,
)


GENERIC_NODE_TYPES = frozenset({"WorldPosInputsNode", "TextureCoordinatesNode", "BreakToComponentsNode"})
PROPERTY_NODE_TYPES = frozenset({"TexturePropertyNode", "RangedFloatNode", "Matrix4X4Node", "Vector4Node"})
PROPERTY_TYPES = frozenset({"Constant", "Property", "InstancedProperty", "Global"})
INPUT_TYPES = frozenset(
    {
        "INT", "FLOAT", "FLOAT2", "FLOAT3", "FLOAT4", "FLOAT3x3", "FLOAT4x4",
        "SAMPLER1D", "SAMPLER2D", "SAMPLER3D", "SAMPLERCUBE", "SAMPLER2DARRAY", "SAMPLERSTATE",
    }
)
OUTPUT_TYPES = frozenset({"INT", "FLOAT", "FLOAT2", "FLOAT3", "FLOAT4", "FLOAT3x3", "FLOAT4x4"})
_ROOT_KEYS = frozenset({"version", "template", "nodes", "connections"})
_TEMPLATE_KEYS = frozenset({"guid", "shader_name"})
_COMMON_NODE_KEYS = frozenset({"alias", "kind", "position"})
_NODE_KEYS = {
    "node": _COMMON_NODE_KEYS | {"type"},
    "property": _COMMON_NODE_KEYS | {"type", "property_name", "inspector_name", "parameter_type"},
    "sampler": _COMMON_NODE_KEYS | {"property_name", "inspector_name", "parameter_type"},
    "custom_expression": _COMMON_NODE_KEYS | {"name", "code", "output_type", "inputs"},
}
_ALIAS = re.compile(r"^[A-Za-z][A-Za-z0-9_-]{0,63}$")
_IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_]{0,63}$")
_PROPERTY_NAME = re.compile(r"^_[A-Za-z][A-Za-z0-9_]{0,126}$")
_GUID = re.compile(r"^[0-9a-fA-F]{32}$")
_CSHARP_MARKERS = re.compile(
    r"(?:\busing\s+(?:System|Unity)|\bUnityEditor\b|\bUnityEngine\b|"
    r"\bSystem\.(?:IO|Reflection|Diagnostics|Runtime|Net)\b|\bDllImport\b|^\s*#r\b)", re.MULTILINE,
)


def parse_editor_graph_spec(value: Any) -> EditorGraphSpec:
    root = _object(value, "spec")
    _unknown(root, _ROOT_KEYS, "spec")
    if root.get("version") != 1:
        raise SpecError("spec version must be integer 1")
    template = _parse_template(root.get("template"))
    raw_nodes = root.get("nodes")
    if not isinstance(raw_nodes, list):
        raise SpecError("spec nodes must be an array")
    if len(raw_nodes) > 128:
        raise SpecError("spec nodes exceeds the v1 limit of 128")
    nodes = tuple(_parse_node(item, index) for index, item in enumerate(raw_nodes))
    aliases = {node.alias for node in nodes}
    if len(aliases) != len(nodes):
        raise SpecError("node alias must be unique")
    property_names = [node.property_name for node in nodes if node.property_name is not None]
    if len(set(property_names)) != len(property_names):
        raise SpecError("property_name must be unique across property and sampler nodes")
    raw_connections = root.get("connections", [])
    if not isinstance(raw_connections, list):
        raise SpecError("spec connections must be an array")
    if len(raw_connections) > 256:
        raise SpecError("spec connections exceeds the v1 limit of 256")
    connections = tuple(_parse_connection(item, index, aliases) for index, item in enumerate(raw_connections))
    if len({(item.destination.node, item.destination.port) for item in connections}) != len(connections):
        raise SpecError("a destination input port may appear only once")
    validate_connections(template, nodes, connections)
    return EditorGraphSpec(version=1, template=template, nodes=nodes, connections=connections)


def _parse_template(value: Any) -> TemplateSpec:
    obj = _object(value, "template")
    _unknown(obj, _TEMPLATE_KEYS, "template")
    guid = _string(obj.get("guid"), "template guid", 32)
    if not _GUID.fullmatch(guid):
        raise SpecError("template guid must be exactly 32 hexadecimal characters")
    shader_name = _safe_text(obj.get("shader_name"), "template shader_name", 255, False)
    if any(char in shader_name for char in ('"', "'", ";", "\\")):
        raise SpecError("template shader_name contains a forbidden quote, separator, or escape")
    return TemplateSpec(guid=guid.lower(), shader_name=shader_name)


def _parse_node(value: Any, index: int) -> NodeSpec:
    label = f"nodes[{index}]"
    obj = _object(value, label)
    kind = obj.get("kind")
    if kind not in _NODE_KEYS:
        raise SpecError(f"{label} has unknown kind {kind!r}")
    _unknown(obj, _NODE_KEYS[kind], label)
    alias = _string(obj.get("alias"), f"{label} alias", 64)
    if not _ALIAS.fullmatch(alias):
        raise SpecError(f"{label} alias must match {_ALIAS.pattern}")
    if alias == "master":
        raise SpecError(f"{label} alias 'master' is reserved")
    position = _position(obj.get("position"), f"{label} position")
    if kind == "node":
        node_type = _string(obj.get("type"), f"{label} type", 64)
        if node_type not in GENERIC_NODE_TYPES:
            raise SpecError(f"{label} type is not in the generic-node allowlist")
        return NodeSpec(alias, kind, position, type=node_type)
    if kind in {"property", "sampler"}:
        return _parse_property_node(obj, label, alias, kind, position)
    name = _safe_text(obj.get("name"), f"{label} name", 128, False)
    code = _safe_text(obj.get("code"), f"{label} code", 65535, True)
    if any(char in code for char in ("@", "$")) or _CSHARP_MARKERS.search(code):
        raise SpecError(f"{label} code contains an ASE delimiter or forbidden C# runtime marker")
    output_type = obj.get("output_type")
    if output_type not in OUTPUT_TYPES:
        raise SpecError(f"{label} output_type must be one of {sorted(OUTPUT_TYPES)}")
    raw_inputs = obj.get("inputs")
    if not isinstance(raw_inputs, list) or not raw_inputs or len(raw_inputs) > 32:
        raise SpecError(f"{label} inputs must contain 1 through 32 entries")
    inputs = tuple(_parse_input(item, label, i) for i, item in enumerate(raw_inputs))
    if len({item.name for item in inputs}) != len(inputs):
        raise SpecError(f"{label} input name must be unique")
    return NodeSpec(alias, kind, position, name=name, code=code, output_type=output_type, inputs=inputs)


def _parse_property_node(obj: dict, label: str, alias: str, kind: str, position: tuple[float, float]) -> NodeSpec:
    node_type = "SamplerNode" if kind == "sampler" else _string(obj.get("type"), f"{label} type", 64)
    allowed = {"SamplerNode"} if kind == "sampler" else PROPERTY_NODE_TYPES
    if node_type not in allowed:
        raise SpecError(f"{label} type is not in the property-node allowlist")
    property_name = _string(obj.get("property_name"), f"{label} property_name", 127)
    if not _PROPERTY_NAME.fullmatch(property_name):
        raise SpecError(f"{label} property_name must be an underscored identifier")
    inspector_name = _safe_text(obj.get("inspector_name"), f"{label} inspector_name", 128, False)
    parameter_type = obj.get("parameter_type")
    if parameter_type not in PROPERTY_TYPES:
        raise SpecError(f"{label} parameter_type must be one of {sorted(PROPERTY_TYPES)}")
    return NodeSpec(alias, kind, position, type=None if kind == "sampler" else node_type,
                    property_name=property_name, inspector_name=inspector_name, parameter_type=parameter_type)


def _parse_input(value: Any, node_label: str, index: int) -> InputSpec:
    label = f"{node_label}.inputs[{index}]"
    obj = _object(value, label)
    _unknown(obj, frozenset({"name", "type"}), label)
    name = _string(obj.get("name"), f"{label} name", 64)
    if not _IDENTIFIER.fullmatch(name):
        raise SpecError(f"{label} name must be an HLSL identifier")
    data_type = obj.get("type")
    if data_type not in INPUT_TYPES:
        raise SpecError(f"{label} type must be one of {sorted(INPUT_TYPES)}")
    return InputSpec(name=name, type=data_type)


def _parse_connection(value: Any, index: int, aliases: set[str]) -> ConnectionSpec:
    label = f"connections[{index}]"
    obj = _object(value, label)
    _unknown(obj, frozenset({"from", "to"}), label)
    source = _parse_endpoint(obj.get("from"), f"{label}.from", aliases)
    destination = _parse_endpoint(obj.get("to"), f"{label}.to", aliases)
    if source.node == "master":
        raise SpecError(f"{label} cannot use master as a source")
    return ConnectionSpec(source=source, destination=destination)


def _parse_endpoint(value: Any, label: str, aliases: set[str]) -> EndpointSpec:
    obj = _object(value, label)
    _unknown(obj, frozenset({"node", "port"}), label)
    node = _string(obj.get("node"), f"{label} node", 64)
    if node != "master" and node not in aliases:
        raise SpecError(f"{label} references unknown node alias {node!r}")
    port = obj.get("port")
    if isinstance(port, bool) or not isinstance(port, int) or not 0 <= port <= 63:
        raise SpecError(f"{label} port must be an integer from 0 through 63")
    return EndpointSpec(node=node, port=port)


def _object(value: Any, label: str) -> dict:
    if not isinstance(value, dict):
        raise SpecError(f"{label} must be a JSON object")
    return value


def _unknown(value: dict, allowed: frozenset[str] | set[str], label: str) -> None:
    unknown = set(value) - set(allowed)
    if unknown:
        raise SpecError(f"{label} has unknown keys: {sorted(unknown)}")


def _string(value: Any, label: str, limit: int) -> str:
    if not isinstance(value, str) or not value or len(value) > limit:
        raise SpecError(f"{label} must be a non-empty string of at most {limit} characters")
    return value


def _safe_text(value: Any, label: str, limit: int, allow_newline: bool) -> str:
    text = _string(value, label, limit)
    if "\x00" in text or (not allow_newline and any(char in text for char in ("\r", "\n", ";"))):
        raise SpecError(f"{label} contains a forbidden control character or separator")
    return text


def _position(value: Any, label: str) -> tuple[float, float]:
    if not isinstance(value, list) or len(value) != 2:
        raise SpecError(f"{label} must be [x, y]")
    result = []
    for item in value:
        if isinstance(item, bool) or not isinstance(item, (int, float)):
            raise SpecError(f"{label} coordinates must be numbers")
        number = float(item)
        if not math.isfinite(number) or abs(number) > 1_000_000:
            raise SpecError(f"{label} coordinates must be finite and within +/-1000000")
        result.append(number)
    return result[0], result[1]
