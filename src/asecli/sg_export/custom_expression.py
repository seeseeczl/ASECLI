"""Certified ASE Custom Expression decoder for SG Custom Function nodes."""

from __future__ import annotations

import re

from .model import SemanticNode, finite, numbers, position


ASE_TYPE_TO_SG = {
    "FLOAT": "Vector1",
    "FLOAT2": "Vector2",
    "FLOAT3": "Vector3",
    "FLOAT4": "Vector4",
    "COLOR": "Vector4",
    "SAMPLER2D": "Texture2D",
    "SAMPLER2DARRAY": "Texture2DArray",
    "SAMPLER3D": "Texture3D",
    "SAMPLERCUBE": "Cubemap",
    "SAMPLERSTATE": "SamplerState",
    "FLOAT2x2": "Matrix2",
    "FLOAT3x3": "Matrix3",
    "FLOAT4x4": "Matrix4",
}


def convert_custom_expression(node, settings):
    fields = node.raw_fields
    if len(fields) < 20 or not fields[9].isdigit():
        raise ValueError("Custom Expression interface is not recognized")
    expression = fields[6]
    count = int(fields[9])
    inputs = {}
    defaults = {}
    ports = []
    index = 10
    for port_id in range(count):
        if index + 7 >= len(fields) or fields[index] != "True":
            raise ValueError("Custom Expression input interface is truncated")
        name, ase_type, raw_default = fields[index + 1:index + 4]
        sg_type = ASE_TYPE_TO_SG.get(ase_type)
        if not re.fullmatch(r"[A-Za-z_]\w*", name) or sg_type is None:
            raise ValueError(f"Custom Expression input {name!r}/{ase_type!r} is unsupported")
        inputs[port_id] = name
        if ase_type in {"FLOAT", "FLOAT2", "FLOAT3", "FLOAT4", "COLOR"}:
            defaults[port_id] = _typed_value(raw_default, ase_type)
        elif raw_default:
            raise ValueError(f"Custom Expression resource default for {name!r} is unsupported")
        ports.append({"name": name, "type": sg_type, "direction": "Input"})
        index += 8
    output_type = ASE_TYPE_TO_SG.get(fields[-2])
    if output_type is None:
        raise ValueError(f"Custom Expression output type {fields[-2]!r} is unsupported")
    ports.insert(0, {"name": "Out", "type": output_type, "direction": "Output"})
    item = SemanticNode(
        node.node_id,
        f"ase_{node.node_id}",
        "custom-function",
        position(node),
        input_names=inputs,
        output_names={0: "Out"},
        defaults=defaults,
        settings=settings,
        function={
            "name": f"ASEExpression_{node.node_id}",
            "source": "String",
            "body": _custom_function_body(expression),
            "ports": ports,
        },
    )
    mapping = {0: (item.target_id, 0)}
    mapping.update({-1 - port: (item.target_id, -1 - port) for port in inputs})
    return [item], [], mapping


def _typed_value(raw, data_type):
    width = {"FLOAT": 1, "FLOAT2": 2, "FLOAT3": 3, "FLOAT4": 4, "COLOR": 4}.get(data_type)
    if width is None:
        raise ValueError(f"default value type {data_type} is not supported")
    return finite(raw) if width == 1 else numbers(raw, width)


def _custom_function_body(expression: str) -> str:
    body = expression.replace("@$", ";\n").replace("@", ";").replace("$", "\n")
    returns = list(re.finditer(r"\breturn\s+(.+?);", body, flags=re.DOTALL))
    if len(returns) > 1:
        raise ValueError("Custom Expression has multiple returns and cannot be safely wrapped")
    if returns:
        match = returns[0]
        body = body[:match.start()] + f"Out = {match.group(1)};" + body[match.end():]
    elif any(token in body for token in (";", "#if", "#else", "#endif")):
        raise ValueError("Custom Expression statement body has no single return")
    else:
        body = f"Out = {body};"
    return body
