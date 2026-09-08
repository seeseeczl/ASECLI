"""Validation implementation split from the public EditorGraphSpec model."""

from __future__ import annotations

from typing import Any

from ._editor_port_contract import validate_connections
from ._editor_spec_grammar import (
    GENERIC_NODE_TYPES,
    OUTPUT_TYPES,
    PROPERTY_NODE_TYPES,
    PROPERTY_TYPES,
    SUPPORTED_PRIMITIVES_VERSIONS,
    _ALIAS,
    _CSHARP_MARKERS,
    _COMMON_NODE_KEYS,
    _GUID,
    _IDENTIFIER,
    _NODE_KEYS_V1,
    _NODE_KEYS_V2,
    _NODE_KEYS_V3,
    _PROPERTY_NAME,
    _ROOT_KEYS,
    _TEMPLATE_KEYS,
    object_dict,
    parse_input,
    parse_precision,
    parse_primitive,
    parse_property_semantics,
    parse_recipe,
    position,
    reject_unknown,
    require_string,
    safe_text,
)
from .editor_spec import (
    ConnectionSpec,
    EditorGraphSpec,
    EndpointSpec,
    InputSpec,
    NodeSpec,
    SpecError,
    TemplateSpec,
)
from ..core import contains_han, validate_enable_if


def parse_editor_graph_spec(value: Any) -> EditorGraphSpec:
    root = object_dict(value, "spec")
    reject_unknown(root, _ROOT_KEYS, "spec")
    version = root.get("version")
    if version not in {1, 2, 3}:
        raise SpecError("spec version must be integer 1, 2, or 3")
    primitives_version = None
    if version == 3:
        primitives_version = root.get("primitives_version")
        if isinstance(primitives_version, bool) or not isinstance(primitives_version, int):
            raise SpecError("spec primitives_version must be an integer")
        if primitives_version not in SUPPORTED_PRIMITIVES_VERSIONS:
            raise SpecError(f"spec primitives_version {primitives_version} is not supported")
    else:
        if "primitives_version" in root:
            raise SpecError("spec primitives_version is only valid for version 3")
    template = _parse_template(root.get("template"))
    raw_nodes = root.get("nodes")
    if not isinstance(raw_nodes, list):
        raise SpecError("spec nodes must be an array")
    if len(raw_nodes) > 128:
        raise SpecError("spec nodes exceeds the v1 limit of 128")
    nodes = tuple(_parse_node(item, index, version) for index, item in enumerate(raw_nodes))
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
    return EditorGraphSpec(
        version=version, template=template, nodes=nodes, connections=connections,
        primitives_version=primitives_version,
    )


def _parse_template(value: Any) -> TemplateSpec:
    obj = object_dict(value, "template")
    reject_unknown(obj, _TEMPLATE_KEYS, "template")
    guid = require_string(obj.get("guid"), "template guid", 32)
    if not _GUID.fullmatch(guid):
        raise SpecError("template guid must be exactly 32 hexadecimal characters")
    shader_name = safe_text(obj.get("shader_name"), "template shader_name", 255, False)
    if any(char in shader_name for char in ('"', "'", ";", "\\")):
        raise SpecError("template shader_name contains a forbidden quote, separator, or escape")
    return TemplateSpec(guid=guid.lower(), shader_name=shader_name)


def _parse_node(value: Any, index: int, version: int) -> NodeSpec:
    label = f"nodes[{index}]"
    obj = object_dict(value, label)
    kind = obj.get("kind")
    if version == 3:
        node_keys = _NODE_KEYS_V3
    elif version == 2:
        node_keys = _NODE_KEYS_V2
    else:
        node_keys = _NODE_KEYS_V1
    if kind not in node_keys:
        raise SpecError(f"{label} has unknown kind {kind!r}")
    reject_unknown(obj, node_keys[kind], label)
    alias = require_string(obj.get("alias"), f"{label} alias", 64)
    if not _ALIAS.fullmatch(alias):
        raise SpecError(f"{label} alias must match {_ALIAS.pattern}")
    if alias == "master":
        raise SpecError(f"{label} alias 'master' is reserved")
    node_position = position(obj.get("position"), f"{label} position")
    precision = parse_precision(obj, label)
    if kind == "node":
        node_type = require_string(obj.get("type"), f"{label} type", 64)
        if node_type not in GENERIC_NODE_TYPES:
            raise SpecError(f"{label} type is not in the generic-node allowlist")
        return NodeSpec(alias, kind, node_position, type=node_type, precision=precision)
    if kind in {"property", "sampler"}:
        return _parse_property_node(obj, label, alias, kind, node_position, version, precision)
    if kind == "primitive":
        return parse_primitive(obj, label, alias, node_position)
    if kind == "recipe":
        return parse_recipe(obj, label, alias, node_position)
    name = safe_text(obj.get("name"), f"{label} name", 128, False)
    code = safe_text(obj.get("code"), f"{label} code", 65535, True)
    if any(char in code for char in ("@", "$")) or _CSHARP_MARKERS.search(code):
        raise SpecError(f"{label} code contains an ASE delimiter or forbidden C# runtime marker")
    output_type = obj.get("output_type")
    if output_type not in OUTPUT_TYPES:
        raise SpecError(f"{label} output_type must be one of {sorted(OUTPUT_TYPES)}")
    raw_inputs = obj.get("inputs")
    if not isinstance(raw_inputs, list) or not raw_inputs or len(raw_inputs) > 32:
        raise SpecError(f"{label} inputs must contain 1 through 32 entries")
    inputs = tuple(parse_input(item, label, i) for i, item in enumerate(raw_inputs))
    if len({item.name for item in inputs}) != len(inputs):
        raise SpecError(f"{label} input name must be unique")
    return NodeSpec(alias, kind, node_position, name=name, code=code, output_type=output_type, inputs=inputs)


def _parse_property_node(
    obj: dict,
    label: str,
    alias: str,
    kind: str,
    node_position: tuple[float, float],
    version: int,
    precision: str | None,
) -> NodeSpec:
    node_type = "SamplerNode" if kind == "sampler" else require_string(obj.get("type"), f"{label} type", 64)
    allowed = {"SamplerNode"} if kind == "sampler" else PROPERTY_NODE_TYPES
    if node_type not in allowed:
        raise SpecError(f"{label} type is not in the property-node allowlist")
    property_name = require_string(obj.get("property_name"), f"{label} property_name", 127)
    if not _PROPERTY_NAME.fullmatch(property_name):
        raise SpecError(f"{label} property_name must be an underscored identifier")
    inspector_name = safe_text(obj.get("inspector_name"), f"{label} inspector_name", 128, False)
    tooltip_text = None
    help_text = None
    enabled_if = None
    if version >= 2:
        if not contains_han(inspector_name):
            raise SpecError(f"{label} inspector_name must contain Chinese characters")
        if "tooltip" in obj:
            tooltip_text = safe_text(obj.get("tooltip"), f"{label} tooltip", 4096, True)
            if "help" in obj:
                help_text = safe_text(obj.get("help"), f"{label} help", 4096, True)
        else:
            tooltip_text = safe_text(obj.get("help"), f"{label} tooltip", 4096, True)
        if not contains_han(tooltip_text):
            raise SpecError(f"{label} tooltip must contain Chinese characters")
        if "enabled_if" in obj:
            try:
                enabled_if = validate_enable_if(obj["enabled_if"])
            except ValueError as exc:
                raise SpecError(f"{label} {exc}") from exc
    parameter_type = obj.get("parameter_type")
    if parameter_type not in PROPERTY_TYPES:
        raise SpecError(f"{label} parameter_type must be one of {sorted(PROPERTY_TYPES)}")
    default, minimum, maximum = parse_property_semantics(obj, label, kind, node_type)
    return NodeSpec(alias, kind, node_position, type=None if kind == "sampler" else node_type,
                    property_name=property_name, inspector_name=inspector_name,
                    tooltip=tooltip_text, help=help_text, enabled_if=enabled_if,
                    parameter_type=parameter_type, precision=precision,
                    default=default, min=minimum, max=maximum)


def _parse_connection(value: Any, index: int, aliases: set[str]) -> ConnectionSpec:
    label = f"connections[{index}]"
    obj = object_dict(value, label)
    reject_unknown(obj, frozenset({"from", "to"}), label)
    source = _parse_endpoint(obj.get("from"), f"{label}.from", aliases)
    destination = _parse_endpoint(obj.get("to"), f"{label}.to", aliases)
    if source.node == "master":
        raise SpecError(f"{label} cannot use master as a source")
    return ConnectionSpec(source=source, destination=destination)


def _parse_endpoint(value: Any, label: str, aliases: set[str]) -> EndpointSpec:
    obj = object_dict(value, label)
    reject_unknown(obj, frozenset({"node", "port"}), label)
    node = require_string(obj.get("node"), f"{label} node", 64)
    if node != "master" and node not in aliases:
        raise SpecError(f"{label} references unknown node alias {node!r}")
    port = obj.get("port")
    if isinstance(port, bool) or not isinstance(port, int) or not 0 <= port <= 63:
        raise SpecError(f"{label} port must be an integer from 0 through 63")
    return EndpointSpec(node=node, port=port)
