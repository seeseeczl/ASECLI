"""Algorithm-primitive closure (op -> ASE class + port contract) for EditorGraphSpec v3.

This module is the single source of truth shared by the model (manifest
synthesis), the port-contract validator, the spec validator, and (mirrored in)
the fixed C# executor. It must import nothing from the rest of the package so
both ``editor_spec`` and ``_editor_port_contract`` may depend on it without a
cycle.
"""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any

DYNAMIC_NUMERIC = "DYNAMIC_NUMERIC"


@dataclass(frozen=True)
class PrimitiveSpec:
    id: str
    op: str
    args: tuple[str, ...] = ()
    value: str | None = None

    def to_dict(self) -> dict:
        result: dict[str, Any] = {"id": self.id, "op": self.op}
        if self.op == "const":
            result["value"] = self.value
        else:
            result["args"] = list(self.args)
        return result


@dataclass(frozen=True)
class ExpansionSpec:
    primitives: tuple[PrimitiveSpec, ...]
    output: str

    def to_dict(self) -> dict:
        return {
            "primitives": [item.to_dict() for item in self.primitives],
            "output": self.output,
        }


_DYN = DYNAMIC_NUMERIC
_FLOAT = "FLOAT"
_FLOAT2 = "FLOAT2"
_FLOAT3 = "FLOAT3"
_FLOAT4 = "FLOAT4"
_COLOR = "COLOR"
_INT = "INT"
_SAMPLER2D = "SAMPLER2D"

# op -> (ASE class name, input ports, output ports).
# Dynamic ports use DYNAMIC_NUMERIC; fixed dimensions are spelled out.
# Arity here is the authoritative ASE 1.9.6.2 runtime shape, verified against
# the local schema dump and AmplifyShaderEditor source.
PRIMITIVE_OPS: dict[str, tuple[str, dict[int, str], dict[int, str]]] = {
    # 3.1 Math / trigonometry (almost all dynamic).
    "add": ("SimpleAddOpNode", {0: _DYN, 1: _DYN}, {0: _DYN}),
    "sub": ("SimpleSubtractOpNode", {0: _DYN, 1: _DYN}, {0: _DYN}),
    "mul": ("SimpleMultiplyOpNode", {0: _DYN, 1: _DYN}, {0: _DYN}),
    "div": ("SimpleDivideOpNode", {0: _DYN, 1: _DYN}, {0: _DYN}),
    "min": ("SimpleMinOpNode", {0: _DYN, 1: _DYN}, {0: _DYN}),
    "max": ("SimpleMaxOpNode", {0: _DYN, 1: _DYN}, {0: _DYN}),
    "remainder": ("SimpleRemainderNode", {0: _DYN, 1: _DYN}, {0: _DYN}),
    "saturate": ("SaturateNode", {0: _DYN}, {0: _DYN}),
    "one_minus": ("OneMinusNode", {0: _DYN}, {0: _DYN}),
    "negate": ("NegateNode", {0: _DYN}, {0: _DYN}),
    "abs": ("AbsOpNode", {0: _DYN}, {0: _DYN}),
    "floor": ("FloorOpNode", {0: _DYN}, {0: _DYN}),
    "ceil": ("CeilOpNode", {0: _DYN}, {0: _DYN}),
    "fract": ("FractNode", {0: _DYN}, {0: _DYN}),
    "round": ("RoundOpNode", {0: _DYN}, {0: _DYN}),
    "trunc": ("TruncOpNode", {0: _DYN}, {0: _DYN}),
    "sign": ("SignOpNode", {0: _DYN}, {0: _DYN}),
    "sqrt": ("SqrtOpNode", {0: _DYN}, {0: _DYN}),
    "rsqrt": ("RSqrtOpNode", {0: _DYN}, {0: _DYN}),
    "rcp": ("ReciprocalOpNode", {0: _DYN}, {0: _DYN}),
    "normalize": ("NormalizeNode", {0: _DYN}, {0: _DYN}),
    "length": ("LengthOpNode", {0: _DYN}, {0: _FLOAT}),
    "clamp": ("ClampOpNode", {0: _DYN, 1: _DYN, 2: _DYN}, {0: _DYN}),
    "step": ("StepOpNode", {0: _DYN, 1: _DYN}, {0: _DYN}),
    "smoothstep": ("SmoothstepOpNode", {0: _DYN, 1: _DYN, 2: _DYN}, {0: _DYN}),
    "lerp": ("LerpOp", {0: _DYN, 1: _DYN, 2: _DYN}, {0: _DYN}),
    "pow": ("PowerNode", {0: _DYN, 1: _DYN}, {0: _DYN}),
    "exp": ("ExpOpNode", {0: _DYN}, {0: _DYN}),
    "exp2": ("Exp2OpNode", {0: _DYN}, {0: _DYN}),
    "log": ("LogOpNode", {0: _DYN}, {0: _DYN}),
    "log2": ("Log2OpNode", {0: _DYN}, {0: _DYN}),
    "log10": ("Log10OpNode", {0: _DYN}, {0: _DYN}),
    "sin": ("SinOpNode", {0: _DYN}, {0: _DYN}),
    "cos": ("CosOpNode", {0: _DYN}, {0: _DYN}),
    "tan": ("TanOpNode", {0: _DYN}, {0: _DYN}),
    "asin": ("ASinOpNode", {0: _DYN}, {0: _DYN}),
    "acos": ("ACosOpNode", {0: _DYN}, {0: _DYN}),
    "atan": ("ATanOpNode", {0: _DYN}, {0: _DYN}),
    "atan2": ("ATan2OpNode", {0: _DYN, 1: _DYN}, {0: _DYN}),
    "sinh": ("SinhOpNode", {0: _DYN}, {0: _DYN}),
    "cosh": ("CoshOpNode", {0: _DYN}, {0: _DYN}),
    "tanh": ("TanhOpNode", {0: _DYN}, {0: _DYN}),
    "radians": ("RadiansOpNode", {0: _DYN}, {0: _DYN}),
    "degrees": ("DegreesOpNode", {0: _DYN}, {0: _DYN}),
    "fmod": ("FmodOpNode", {0: _DYN, 1: _DYN}, {0: _DYN}),
    "remap": ("TFHCRemapNode", {0: _DYN, 1: _DYN, 2: _DYN, 3: _DYN, 4: _DYN}, {0: _DYN}),
    "dot": ("DotProductOpNode", {0: _DYN, 1: _DYN}, {0: _FLOAT}),
    "cross": ("CrossProductOpNode", {0: _FLOAT3, 1: _FLOAT3}, {0: _FLOAT3}),
    "distance": ("DistanceOpNode", {0: _DYN, 1: _DYN}, {0: _FLOAT}),
    "reflect": ("ReflectOpNode", {0: _DYN, 1: _DYN}, {0: _DYN}),
    "refract": ("RefractOpVec", {0: _DYN, 1: _DYN, 2: _DYN}, {0: _DYN}),
    # ASE RotateAboutAxisNode takes 4 inputs (axis, angle, pivot, position).
    "rotate_axis": ("RotateAboutAxisNode",
                     {0: _FLOAT3, 1: _FLOAT, 2: _FLOAT3, 3: _FLOAT3}, {0: _FLOAT3}),

    # 3.2 Vector / channel / constant.
    "append": ("DynamicAppendNode", {0: _FLOAT, 1: _FLOAT, 2: _FLOAT, 3: _FLOAT}, {0: _FLOAT4}),
    "swizzle": ("SwizzleNode", {0: _DYN}, {0: _DYN}),
    "component_mask": ("ComponentMaskNode", {0: _DYN}, {0: _DYN}),
    "split": ("BreakToComponentsNode", {0: _DYN}, {port: _FLOAT for port in range(16)}),
    # "const" is shape-dispatched at runtime; not a fixed ASE class.

    # 3.3 Image / color / logic.
    "luminance": ("LuminanceNode", {0: _DYN}, {0: _DYN}),
    "desaturate": ("DesaturateOpNode", {0: _DYN, 1: _DYN}, {0: _DYN}),
    "contrast": ("SimpleContrastOpNode", {0: _DYN, 1: _DYN}, {0: _DYN}),
    "posterize": ("PosterizeNode", {0: _COLOR, 1: _INT}, {0: _COLOR}),
    "rgb_to_hsv": ("RGBToHSVNode", {0: _FLOAT3}, {0: _FLOAT3, 1: _FLOAT, 2: _FLOAT, 3: _FLOAT}),
    "hsv_to_rgb": ("HSVToRGBNode", {0: _FLOAT, 1: _FLOAT, 2: _FLOAT},
                   {0: _FLOAT3, 1: _FLOAT, 2: _FLOAT, 3: _FLOAT}),
    "gamma_to_linear": ("GammaToLinearNode", {0: _DYN}, {0: _DYN}),
    "linear_to_gamma": ("LinearToGammaNode", {0: _DYN}, {0: _DYN}),
    "not": ("NotNode", {0: _DYN}, {0: _DYN}),
    "nand": ("NandNode", {0: _DYN, 1: _DYN}, {0: _DYN}),
    # ASE AllOpNode / AnyOpNode are unary "all/any components non-zero".
    "and": ("AllOpNode", {0: _DYN}, {0: _DYN}),
    "or": ("AnyOpNode", {0: _DYN}, {0: _DYN}),
    # ASE StaticSwitch is a 9-input keyword toggle; ConditionalIfNode is a 5-input compare.
    "select": ("StaticSwitch", {port: _FLOAT for port in range(9)}, {0: _DYN}),

    # 3.4 Input / context primitives.
    "texcoord": ("TextureCoordinatesNode",
                 {0: _FLOAT2, 1: _FLOAT2, 2: _SAMPLER2D},
                 {0: _FLOAT2, 1: _FLOAT, 2: _FLOAT, 3: _FLOAT, 4: _FLOAT}),
    "world_position": ("WorldPosInputsNode", {}, {0: _FLOAT3, 1: _FLOAT, 2: _FLOAT, 3: _FLOAT}),
    "time": ("SimpleTimeNode", {0: _FLOAT}, {0: _FLOAT}),
    "vertex_color": ("VertexColorNode", {}, {0: _COLOR, 1: _FLOAT, 2: _FLOAT, 3: _FLOAT, 4: _FLOAT}),
    "vertex_id": ("VertexIdVariableNode", {}, {0: _INT}),
    "instance_id": ("InstanceIdNode", {}, {0: _INT}),
    "world_normal": ("WorldNormalVector", {0: _FLOAT3}, {0: _FLOAT3, 1: _FLOAT, 2: _FLOAT, 3: _FLOAT}),
}


_VEC_CONST = re.compile(r"^\s*float([234])\s*\(\s*(.+?)\s*\)\s*$")
_NUMBER = re.compile(r"^[+-]?(\d+(\.\d*)?|\.\d+)([eE][+-]?\d+)?$")


def const_class(value: str) -> str:
    """ASE class for a const literal, dispatched by HLSL shape."""
    if _NUMBER.fullmatch(value.strip()):
        return "RangedFloatNode"
    match = _VEC_CONST.match(value)
    if match:
        return {"2": "Vector2Node", "3": "Vector3Node", "4": "Vector4Node"}[match.group(1)]
    raise ValueError(f"unsupported const literal shape: {value!r}")


def const_output_type(value: str) -> str:
    if _NUMBER.fullmatch(value.strip()):
        return "FLOAT"
    match = _VEC_CONST.match(value)
    if match:
        return "FLOAT" + match.group(1)
    raise ValueError(f"unsupported const literal shape: {value!r}")


def primitive_class(op: str) -> str | None:
    """ASE class for an op, or None when the op is not in the closure."""
    entry = PRIMITIVE_OPS.get(op)
    return entry[0] if entry else None


def is_known_op(op: str) -> bool:
    return op in PRIMITIVE_OPS


def expansion_classes(primitives: object) -> list[str] | None:
    """Resolve each recipe expansion primitive to its ASE class.

    Returns ``None`` when any primitive cannot be resolved (which signals the
    executor to fall back to ``CustomExpressionNode``), otherwise a list of ASE
    class names aligned with the primitive order.
    """
    classes: list[str] = []
    for primitive in primitives:  # type: ignore[union-attr]
        op = primitive.op
        if op == "const":
            classes.append(const_class(primitive.value))
            continue
        cls = primitive_class(op)
        if cls is None:
            return None
        classes.append(cls)
    return classes
