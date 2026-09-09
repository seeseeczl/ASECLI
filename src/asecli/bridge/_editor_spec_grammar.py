"""Shared grammar constants, helpers and v3 parsing for EditorGraphSpec validation."""

from __future__ import annotations

import math
import re
from typing import Any

from ._editor_primitives import ExpansionSpec, PrimitiveSpec, const_output_type, is_known_op
from .editor_spec import InputSpec, NodeSpec, SpecError


GENERIC_NODE_TYPES = frozenset({"WorldPosInputsNode", "TextureCoordinatesNode", "BreakToComponentsNode", "SimpleAddOpNode", "SimpleSubtractOpNode", "SimpleMultiplyOpNode", "SimpleDivideOpNode", "SimpleMinOpNode", "SimpleMaxOpNode", "SaturateNode", "OneMinusNode", "LerpOp"})
PROPERTY_NODE_TYPES = frozenset({"TexturePropertyNode", "RangedFloatNode", "Matrix4X4Node", "Vector4Node", "ColorNode"})
PROPERTY_TYPES = frozenset({"Constant", "Property", "InstancedProperty", "Global"})
SUPPORTED_PRIMITIVES_VERSIONS = frozenset({1})
PRECISION_TYPES = frozenset({"Float", "Half", "Inherit"})
INPUT_TYPES = frozenset(
    {
        "INT", "FLOAT", "FLOAT2", "FLOAT3", "FLOAT4", "FLOAT3x3", "FLOAT4x4",
        "SAMPLER1D", "SAMPLER2D", "SAMPLER3D", "SAMPLERCUBE", "SAMPLER2DARRAY", "SAMPLERSTATE",
    }
)
OUTPUT_TYPES = frozenset({"INT", "FLOAT", "FLOAT2", "FLOAT3", "FLOAT4", "FLOAT3x3", "FLOAT4x4"})
_ROOT_KEYS = frozenset({"version", "template", "nodes", "connections", "primitives_version"})
_TEMPLATE_KEYS = frozenset({"guid", "shader_name", "settings"})
_COMMON_NODE_KEYS = frozenset({"alias", "kind", "position"})
_NODE_KEYS_V1 = {
    "node": _COMMON_NODE_KEYS | {"type"},
    "property": _COMMON_NODE_KEYS | {"type", "property_name", "inspector_name", "parameter_type"},
    "sampler": _COMMON_NODE_KEYS | {"property_name", "inspector_name", "parameter_type"},
    "custom_expression": _COMMON_NODE_KEYS | {"name", "code", "output_type", "inputs"},
}
_NODE_KEYS_V2 = {
    **_NODE_KEYS_V1,
    "node": _NODE_KEYS_V1["node"] | {"precision"},
    "custom_expression": _NODE_KEYS_V1["custom_expression"] | {"precision"},
    "property": _NODE_KEYS_V1["property"] | {"help", "tooltip", "enabled_if", "precision", "default", "min", "max", "hdr"},
    "sampler": _NODE_KEYS_V1["sampler"] | {"help", "tooltip", "enabled_if", "precision", "texture_guid", "hidden"},
}
_NODE_KEYS_V3 = {
    **_NODE_KEYS_V2,
    "primitive": _COMMON_NODE_KEYS | {"op"},
    "recipe": _COMMON_NODE_KEYS | {"recipe", "code", "output_type", "inputs", "expansion"},
}
_ALIAS = re.compile(r"^[A-Za-z][A-Za-z0-9_-]{0,63}$")
_IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_]{0,63}$")
_PROPERTY_NAME = re.compile(r"^_[A-Za-z][A-Za-z0-9_]{0,126}$")
_GUID = re.compile(r"^[0-9a-fA-F]{32}$")
_CSHARP_MARKERS = re.compile(
    r"(?:\busing\s+(?:System|Unity)|\bUnityEditor\b|\bUnityEngine\b|"
    r"\bSystem\.(?:IO|Reflection|Diagnostics|Runtime|Net)\b|\bDllImport\b|^\s*#r\b)", re.MULTILINE,
)


def parse_precision(obj: dict, label: str) -> str | None:
    if "precision" not in obj:
        return None
    precision = obj.get("precision")
    if not isinstance(precision, str) or precision not in PRECISION_TYPES:
        raise SpecError(f"{label} precision must be one of {sorted(PRECISION_TYPES)}")
    return precision


def parse_primitive(obj: dict, label: str, alias: str, position: tuple[float, float]) -> NodeSpec:
    op = _string(obj.get("op"), f"{label} op", 64)
    if not is_known_op(op):
        raise SpecError(f"{label} op {op!r} is not in the algorithm-primitive closure")
    return NodeSpec(alias, "primitive", position, op=op)


def parse_recipe(obj: dict, label: str, alias: str, position: tuple[float, float]) -> NodeSpec:
    recipe = _string(obj.get("recipe"), f"{label} recipe", 64)
    code = _safe_text(obj.get("code"), f"{label} code", 65535, True)
    if any(char in code for char in ("@", "$")) or _CSHARP_MARKERS.search(code):
        raise SpecError(f"{label} code contains an ASE delimiter or forbidden C# runtime marker")
    output_type = obj.get("output_type")
    if output_type not in OUTPUT_TYPES:
        raise SpecError(f"{label} output_type must be one of {sorted(OUTPUT_TYPES)}")
    raw_inputs = obj.get("inputs")
    if not isinstance(raw_inputs, list) or not raw_inputs or len(raw_inputs) > 32:
        raise SpecError(f"{label} inputs must contain 1 through 32 entries")
    inputs = tuple(parse_input(item, label, i) for i, item in enumerate(raw_inputs))
    input_names = {item.name for item in inputs}
    if len(input_names) != len(inputs):
        raise SpecError(f"{label} input name must be unique")
    expansion = _parse_expansion(obj.get("expansion"), label, inputs)
    return NodeSpec(alias, "recipe", position, recipe=recipe, code=code,
                    output_type=output_type, inputs=inputs, expansion=expansion)


def _parse_expansion(value: Any, label: str, inputs: tuple[InputSpec, ...]) -> ExpansionSpec:
    obj = _object(value, f"{label} expansion")
    _unknown(obj, frozenset({"primitives", "output"}), f"{label} expansion")
    raw = obj.get("primitives")
    if not isinstance(raw, list) or not raw:
        raise SpecError(f"{label} expansion.primitives must be a non-empty array")
    primitives = tuple(_parse_primitive_entry(item, label, i) for i, item in enumerate(raw))
    ids = [item.id for item in primitives]
    if len(set(ids)) != len(ids):
        raise SpecError(f"{label} expansion primitive id must be unique")
    input_names = {item.name for item in inputs}
    declared: set[str] = set(input_names)
    for primitive in primitives:
        if primitive.op == "const":
            if primitive.args:
                raise SpecError(f"{label} expansion const primitive must not declare args")
            if primitive.value is None:
                raise SpecError(f"{label} expansion const primitive must declare value")
            try:
                const_output_type(primitive.value)
            except ValueError as exc:
                raise SpecError(f"{label} expansion const value {exc}") from exc
        else:
            if primitive.value is not None:
                raise SpecError(f"{label} expansion non-const primitive must not declare value")
            for arg in primitive.args:
                if arg not in declared:
                    raise SpecError(f"{label} expansion arg {arg!r} references an undeclared id or input")
        declared.add(primitive.id)
    output = obj.get("output")
    if not isinstance(output, str) or not output or output not in declared:
        raise SpecError(f"{label} expansion.output must reference a declared id or input name")
    return ExpansionSpec(primitives=primitives, output=output)


def _parse_primitive_entry(value: Any, node_label: str, index: int) -> PrimitiveSpec:
    label = f"{node_label} expansion.primitives[{index}]"
    obj = _object(value, label)
    _unknown(obj, frozenset({"id", "op", "args", "value"}), label)
    pid = _string(obj.get("id"), f"{label} id", 64)
    if not _IDENTIFIER.fullmatch(pid):
        raise SpecError(f"{label} id must be an HLSL identifier")
    op = _string(obj.get("op"), f"{label} op", 64)
    args = obj.get("args")
    if args is None:
        arg_tuple: tuple[str, ...] = ()
    elif isinstance(args, list):
        arg_tuple = tuple(_string(item, f"{label} args", 64) for item in args)
    else:
        raise SpecError(f"{label} args must be an array")
    value = obj.get("value")
    if value is not None and not isinstance(value, str):
        raise SpecError(f"{label} value must be a string")
    return PrimitiveSpec(id=pid, op=op, args=arg_tuple, value=value)


def parse_property_semantics(
    obj: dict, label: str, kind: str, node_type: str,
) -> tuple[Any, float | None, float | None]:
    default = obj.get("default")
    minimum = obj.get("min")
    maximum = obj.get("max")
    if kind == "sampler":
        if default is not None or minimum is not None or maximum is not None:
            raise SpecError(f"{label} sampler does not accept default/min/max")
        return None, None, None
    if node_type == "RangedFloatNode":
        if default is not None:
            if isinstance(default, bool) or not isinstance(default, (int, float)) or not math.isfinite(float(default)):
                raise SpecError(f"{label} default must be a finite number")
            default = float(default)
        if (minimum is None) != (maximum is None):
            raise SpecError(f"{label} min and max must appear together")
        if minimum is not None:
            if isinstance(minimum, bool) or not isinstance(minimum, (int, float)):
                raise SpecError(f"{label} min must be a number")
            if isinstance(maximum, bool) or not isinstance(maximum, (int, float)):
                raise SpecError(f"{label} max must be a number")
            minimum = float(minimum)
            maximum = float(maximum)
            if minimum > maximum:
                raise SpecError(f"{label} min must not exceed max")
        return default, minimum, maximum
    if node_type in {"Vector4Node", "ColorNode"}:
        if default is not None:
            if not isinstance(default, list) or len(default) != 4 or any(
                isinstance(item, bool) or not isinstance(item, (int, float)) for item in default
            ):
                raise SpecError(f"{label} default must be a 4-number array")
            default = [float(item) for item in default]
        if minimum is not None or maximum is not None:
            raise SpecError(f"{label} min/max only apply to RangedFloatNode")
        return default, None, None
    if default is not None or minimum is not None or maximum is not None:
        raise SpecError(f"{label} default/min/max only apply to RangedFloatNode or Vector4Node")
    return None, None, None


def parse_input(value: Any, node_label: str, index: int) -> InputSpec:
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


def object_dict(value: Any, label: str) -> dict:
    if not isinstance(value, dict):
        raise SpecError(f"{label} must be a JSON object")
    return value


def reject_unknown(value: dict, allowed: frozenset[str] | set[str], label: str) -> None:
    unknown = set(value) - set(allowed)
    if unknown:
        raise SpecError(f"{label} has unknown keys: {sorted(unknown)}")


def require_string(value: Any, label: str, limit: int) -> str:
    if not isinstance(value, str) or not value or len(value) > limit:
        raise SpecError(f"{label} must be a non-empty string of at most {limit} characters")
    return value


def safe_text(value: Any, label: str, limit: int, allow_newline: bool) -> str:
    text = require_string(value, label, limit)
    if "\x00" in text or (not allow_newline and any(char in text for char in ("\r", "\n", ";"))):
        raise SpecError(f"{label} contains a forbidden control character or separator")
    return text


def position(value: Any, label: str) -> tuple[float, float]:
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


_object = object_dict
_unknown = reject_unknown
_string = require_string
_safe_text = safe_text
_position = position
