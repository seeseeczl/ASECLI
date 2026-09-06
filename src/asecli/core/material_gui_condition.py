"""Portable conditional-enable metadata for MZGUI-compatible inspectors."""

from __future__ import annotations

import math
import re


ENABLE_IF_ATTRIBUTE = "EnableIfMzgui"
ENABLE_IF_OPERATORS = (
    "Less",
    "LessEqual",
    "Equal",
    "NotEqual",
    "GreaterEqual",
    "Greater",
)
_PROPERTY_NAME = re.compile(r"^_[A-Za-z][A-Za-z0-9_]{0,127}$")


def enable_if_attribute(property_name: str, operator: str, value: int | float) -> str:
    """Encode one conditional-enable rule as a ShaderLab property attribute."""
    condition = validate_enable_if(
        {"property": property_name, "operator": operator, "value": value}
    )
    number = format(condition["value"], ".9g")
    return (
        f'[{ENABLE_IF_ATTRIBUTE}({condition["property"]},'
        f'{condition["operator"]},{number})]'
    )


def parse_enable_if_arguments(arguments: str) -> dict:
    """Decode the comma-separated payload stored by EnableIfMzgui."""
    parts = [part.strip() for part in arguments.split(",")]
    if len(parts) != 3:
        raise ValueError("EnableIfMzgui requires property, operator, and numeric value")
    try:
        value = float(parts[2])
    except ValueError as exc:
        raise ValueError("EnableIfMzgui value must be a finite number") from exc
    return validate_enable_if(
        {"property": parts[0], "operator": parts[1], "value": value}
    )


def validate_enable_if(value: object) -> dict:
    """Validate a JSON-compatible conditional-enable object."""
    if not isinstance(value, dict):
        raise ValueError("enabled_if must be an object")
    unknown = set(value) - {"property", "operator", "value"}
    if unknown:
        raise ValueError(f"enabled_if has unknown keys: {sorted(unknown)}")
    property_name = value.get("property")
    if not isinstance(property_name, str) or not _PROPERTY_NAME.fullmatch(property_name):
        raise ValueError("enabled_if.property must be an underscored Shader property name")
    operator = value.get("operator", "Equal")
    if operator not in ENABLE_IF_OPERATORS:
        raise ValueError(
            "enabled_if.operator must be one of " + ", ".join(ENABLE_IF_OPERATORS)
        )
    number = value.get("value")
    if isinstance(number, bool) or not isinstance(number, (int, float)):
        raise ValueError("enabled_if.value must be a finite number")
    number = float(number)
    if not math.isfinite(number):
        raise ValueError("enabled_if.value must be a finite number")
    return {"property": property_name, "operator": operator, "value": number}
