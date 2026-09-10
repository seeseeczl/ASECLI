"""Certified ASE node decoders used by the SG export pipeline."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ..core.model import NodeLine, WireLine
from .model import SemanticNode, finite, numbers, position
from .sources import property_spec, resolve_asset

DIRECT_RULES = {
    "AmplifyShaderEditor.SimpleAddOpNode": ("add", {0: "A", 1: "B"}, {0: "Out"}),
    "AmplifyShaderEditor.SimpleSubtractOpNode": ("subtract", {0: "A", 1: "B"}, {0: "Out"}),
    "AmplifyShaderEditor.SimpleMultiplyOpNode": ("multiply", {0: "A", 1: "B"}, {0: "Out"}),
    "AmplifyShaderEditor.SimpleDivideOpNode": ("divide", {0: "A", 1: "B"}, {0: "Out"}),
    "AmplifyShaderEditor.LerpOp": ("lerp", {0: "A", 1: "B", 2: "T"}, {0: "Out"}),
    "AmplifyShaderEditor.ClampOpNode": ("clamp", {0: "In", 1: "Min", 2: "Max"}, {0: "Out"}),
    "AmplifyShaderEditor.SaturateNode": ("saturate", {0: "In"}, {0: "Out"}),
    "AmplifyShaderEditor.OneMinusNode": ("one-minus", {0: "In"}, {0: "Out"}),
    "AmplifyShaderEditor.BreakToComponentsNode": (
        "split", {0: "In"}, {0: "R", 1: "G", 2: "B", 3: "A"},
    ),
    "AmplifyShaderEditor.DynamicAppendNode": (
        "combine", {0: "R", 1: "G", 2: "B", 3: "A"}, {0: "RGBA"},
    ),
}
CONSTANT_TYPES = {
    "AmplifyShaderEditor.RangedFloatNode": ("float", "float", 1),
    "AmplifyShaderEditor.Vector2Node": ("vector2", "vector2", 2),
    "AmplifyShaderEditor.Vector3Node": ("vector3", "vector3", 3),
    "AmplifyShaderEditor.Vector4Node": ("vector4", "vector4", 4),
    "AmplifyShaderEditor.ColorNode": ("vector4", "color", 4),
}
UV_TYPE = "AmplifyShaderEditor.TextureCoordinatesNode"
SAMPLER_TYPE = "AmplifyShaderEditor.SamplerNode"


def convert_node(node: NodeLine, wires: list[WireLine], compiled: dict, target: Path,
                 asset_map: dict[str, str]):
    """Return semantic nodes, properties and an ASE-port endpoint map."""
    settings = _precision(node)
    if node.type_name in DIRECT_RULES:
        alias, inputs, outputs = DIRECT_RULES[node.type_name]
        connected = {int(w.in_port) for w in wires if w.in_node == node.node_id}
        defaults = {p: v for p, v in _input_defaults(node).items() if p not in connected}
        item = SemanticNode(node.node_id, f"ase_{node.node_id}", alias, position(node),
                            inputs, outputs, defaults, settings)
        mapping = {p: (item.target_id, p) for p in outputs}
        mapping.update({-1 - p: (item.target_id, -1 - p) for p in inputs})
        return [item], [], mapping
    if node.type_name in CONSTANT_TYPES:
        return _constant_node(node, wires, compiled, settings)
    if node.type_name == UV_TYPE:
        defaults = _uv_defaults(node)
        if defaults != {0: [1.0, 1.0], 1: [0.0, 0.0]}:
            raise ValueError("transformed Texture Coordinates are not certified")
        item = SemanticNode(node.node_id, f"ase_{node.node_id}", "uv", position(node),
                            output_names={0: "Out"}, settings=settings)
        return [item], [], {0: (item.target_id, 0)}
    if node.type_name == SAMPLER_TYPE:
        return _texture_node(node, wires, compiled, target, asset_map, settings)
    raise ValueError(f"{node.type_name} has no certified ASE to Shader Graph mapping")


def _constant_node(node, wires, compiled, settings):
    target_type, property_type, width = CONSTANT_TYPES[node.type_name]
    parameter = node.raw_fields[6] if len(node.raw_fields) > 6 else ""
    if parameter not in {"Constant", "Property"}:
        raise ValueError(f"{node.type_name} parameter type {parameter!r} is not supported")
    value = _constant_value(node, width)
    base_id = f"ase_{node.node_id}"
    props = []
    if parameter == "Property":
        prop = property_spec(node, property_type, compiled, value)
        props.append(prop)
        base = SemanticNode(node.node_id, base_id, "property", position(node),
                            output_names={0: "Out"}, property_name=prop["name"])
    else:
        channels = "XYZW"[:width]
        values = [value] if width == 1 else value
        base = SemanticNode(node.node_id, base_id, target_type, position(node),
                            {i: c for i, c in enumerate(channels)}, {0: "Out"},
                            dict(enumerate(values)), settings)
    created = [base]
    mapping = {0: (base_id, 0)}
    used = sorted({int(w.out_port) for w in wires if w.out_node == node.node_id and int(w.out_port) > 0})
    if used:
        if any(port > width for port in used):
            raise ValueError(f"component output {max(used)} exceeds {property_type} width {width}")
        split_id = f"{base_id}_split"
        split = SemanticNode(node.node_id, split_id, "split", [position(node)[0] + 240, position(node)[1]],
                             {0: "In"}, {0: "R", 1: "G", 2: "B", 3: "A"})
        base.source_ids.append(split_id)
        created.append(split)
        mapping.update({port: (split_id, port - 1) for port in used})
        mapping[-1000] = (split_id, -1)
    return created, props, mapping


def _texture_node(node, wires, compiled, target, asset_map, settings):
    fields = node.raw_fields
    if len(fields) < 40 or fields[6] != "Property":
        raise ValueError("Texture Sample must be a certified Texture2D property")
    prop = property_spec(node, "texture2d", compiled, None)
    if fields[31] != "Texture2D" or fields[27] not in {"", "False"}:
        raise ValueError("texture dimension or unpack mode is not certified")
    if fields[30] not in {"Auto", "0"}:
        raise ValueError(f"texture mip mode {fields[30]!r} is not certified")
    guid = fields[20].strip() if len(fields) > 20 else ""
    if guid and guid not in {"None", "0", "-1"}:
        prop["default"] = resolve_asset(guid, target, asset_map)
    base = f"ase_{node.node_id}"
    property_id = f"{base}_property"
    at = position(node)
    property_node = SemanticNode(node.node_id, property_id, "property", at,
                                 output_names={0: "Out"}, property_name=prop["name"],
                                 source_ids=[base])
    inputs = {0: "Texture", 1: "UV", 7: "Sampler"}
    connected = {int(w.in_port) for w in wires if w.in_node == node.node_id}
    inputs = {p: name for p, name in inputs.items() if p in connected or p == 0}
    sample = SemanticNode(node.node_id, base, "sample-texture", [at[0] + 240, at[1]],
                          inputs, {0: "RGBA", 1: "R", 2: "G", 3: "B", 4: "A"},
                          settings=settings)
    mapping = {p: (base, p) for p in sample.output_names}
    mapping.update({-1 - p: (base, -1 - p) for p in inputs})
    mapping[-1000] = (base, -1)
    return [property_node, sample], [prop], mapping


def _constant_value(node, width):
    fields = node.raw_fields
    marker = _find_tail(fields, ["1", "FLOAT", "0"]) if width == 1 else _find_tail(fields, ["5" if width == 4 else str(width + 1)])
    if width == 1:
        return finite(fields[marker - 5])
    offset = 4 if node.type_name == "AmplifyShaderEditor.ColorNode" else 3
    return numbers(fields[marker - offset], width)


def _input_defaults(node):
    fields = node.raw_fields[6:]
    fixed = {"AmplifyShaderEditor.LerpOp": 3, "AmplifyShaderEditor.ClampOpNode": 3,
             "AmplifyShaderEditor.SaturateNode": 1, "AmplifyShaderEditor.OneMinusNode": 1,
             "AmplifyShaderEditor.SimpleSubtractOpNode": 2, "AmplifyShaderEditor.SimpleDivideOpNode": 2,
             "AmplifyShaderEditor.BreakToComponentsNode": 1}
    count = fixed.get(node.type_name)
    start = 2 if node.type_name == "AmplifyShaderEditor.BreakToComponentsNode" else 1
    if count is None and node.type_name in {"AmplifyShaderEditor.SimpleAddOpNode", "AmplifyShaderEditor.SimpleMultiplyOpNode", "AmplifyShaderEditor.DynamicAppendNode"}:
        count, start = int(fields[1]), 2
    if count is None:
        return {}
    result = {}
    for index in range(count):
        base = start + index * 4
        port, data_type, raw, connected = int(fields[base]), fields[base + 1], fields[base + 2], fields[base + 3]
        if connected != "True":
            result[port] = _typed_value(raw, data_type)
    return result


def _uv_defaults(node):
    fields = node.raw_fields[6:]
    return {0: _typed_value(fields[10], fields[9]), 1: _typed_value(fields[14], fields[13])}


def _typed_value(raw, data_type):
    width = {"FLOAT": 1, "FLOAT2": 2, "FLOAT3": 3, "FLOAT4": 4, "COLOR": 4}.get(data_type)
    if width is None:
        raise ValueError(f"default value type {data_type} is not supported")
    return finite(raw) if width == 1 else numbers(raw, width)


def _find_tail(fields, pattern):
    for index in range(len(fields) - len(pattern), -1, -1):
        if fields[index:index + len(pattern)] == pattern:
            return index
    raise ValueError(f"certified value tail {pattern!r} was not found")


def _precision(node):
    value = node.raw_fields[4] if len(node.raw_fields) > 4 else ""
    mapped = {"Float": "Single", "Half": "Half"}.get(value)
    return {"precision": mapped} if mapped else {}
