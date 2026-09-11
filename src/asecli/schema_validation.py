"""Small deterministic validator for the JSON-Schema subset used by CLI contracts."""

from __future__ import annotations

import math
import re
from typing import Any


class SchemaValidationError(ValueError):
    """A value does not satisfy its packaged consumer-owned contract."""


SUPPORTED_SCHEMA_KEYWORDS = frozenset({
    "$comment", "$defs", "$id", "$ref", "$schema", "additionalProperties",
    "allOf", "anyOf", "const", "contains", "else", "enum", "if", "items",
    "maxItems", "maxLength", "maximum", "minItems", "minLength",
    "minProperties", "minimum", "not", "oneOf", "pattern", "prefixItems",
    "properties", "propertyNames", "required", "then", "title", "type",
    "uniqueItems",
})


def validate_schema(instance: Any, schema: Any) -> None:
    unsupported = unsupported_schema_keywords(schema)
    if unsupported:
        raise SchemaValidationError(
            "schema uses unsupported validation keywords: " + ", ".join(unsupported)
        )
    errors: list[str] = []
    _validate(instance, schema, schema, "$", errors)
    if errors:
        raise SchemaValidationError("; ".join(errors[:8]))


def _validate(value: Any, rule: Any, root: dict[str, Any], path: str, errors: list[str]) -> None:
    if rule is True:
        return
    if rule is False:
        errors.append(f"{path}: rejected by schema")
        return
    if not isinstance(rule, dict):
        errors.append(f"{path}: invalid schema rule")
        return
    reference = rule.get("$ref")
    if reference is not None:
        _validate(value, _resolve_reference(root, reference), root, path, errors)
    if "allOf" in rule:
        for branch in rule["allOf"]:
            _validate(value, branch, root, path, errors)
    if "anyOf" in rule and not any(_matches(value, branch, root, path) for branch in rule["anyOf"]):
        errors.append(f"{path}: does not match any allowed schema")
    if "oneOf" in rule:
        matched = sum(_matches(value, branch, root, path) for branch in rule["oneOf"])
        if matched != 1:
            errors.append(f"{path}: must match exactly one schema (matched {matched})")
    if "not" in rule and _matches(value, rule["not"], root, path):
        errors.append(f"{path}: matches a forbidden schema")
    if "if" in rule:
        branch = rule.get("then") if _matches(value, rule["if"], root, path) else rule.get("else")
        if branch is not None:
            _validate(value, branch, root, path, errors)
    if "const" in rule and not _json_equal(value, rule["const"]):
        errors.append(f"{path}: expected constant {rule['const']!r}")
    if "enum" in rule and not any(_json_equal(value, item) for item in rule["enum"]):
        errors.append(f"{path}: value is not in the allowed enum")
    expected_type = rule.get("type")
    if expected_type is not None and not _is_type(value, expected_type):
        errors.append(f"{path}: expected type {expected_type!r}")
        return
    if isinstance(value, dict):
        _validate_object(value, rule, root, path, errors)
    elif isinstance(value, list):
        _validate_array(value, rule, root, path, errors)
    elif isinstance(value, str):
        if len(value) < rule.get("minLength", 0):
            errors.append(f"{path}: string is shorter than minLength")
        if "maxLength" in rule and len(value) > rule["maxLength"]:
            errors.append(f"{path}: string is longer than maxLength")
        if "pattern" in rule and re.search(rule["pattern"], value) is None:
            errors.append(f"{path}: string does not match {rule['pattern']!r}")
    elif _is_number(value):
        if "minimum" in rule and value < rule["minimum"]:
            errors.append(f"{path}: number is below minimum")
        if "maximum" in rule and value > rule["maximum"]:
            errors.append(f"{path}: number is above maximum")


def _validate_object(value, rule, root, path, errors):
    for name in rule.get("required", []):
        if name not in value:
            errors.append(f"{path}: missing required property {name!r}")
    if len(value) < rule.get("minProperties", 0):
        errors.append(f"{path}: object has fewer than minProperties")
    properties = rule.get("properties", {})
    for name, item in value.items():
        if "propertyNames" in rule:
            _validate(name, rule["propertyNames"], root, f"{path}.{name}<name>", errors)
        if name in properties:
            _validate(item, properties[name], root, f"{path}.{name}", errors)
        elif rule.get("additionalProperties") is False:
            errors.append(f"{path}: unknown property {name!r}")
        elif isinstance(rule.get("additionalProperties"), dict):
            _validate(item, rule["additionalProperties"], root, f"{path}.{name}", errors)


def _validate_array(value, rule, root, path, errors):
    if len(value) < rule.get("minItems", 0):
        errors.append(f"{path}: array has fewer than minItems")
    if "maxItems" in rule and len(value) > rule["maxItems"]:
        errors.append(f"{path}: array has more than maxItems")
    if rule.get("uniqueItems"):
        if any(
            _json_equal(value[left], value[right])
            for left in range(len(value))
            for right in range(left + 1, len(value))
        ):
            errors.append(f"{path}: array items must be unique")
    if "contains" in rule and not any(
        _matches(item, rule["contains"], root, f"{path}[{index}]")
        for index, item in enumerate(value)
    ):
        errors.append(f"{path}: array does not contain a required item")
    prefix = rule.get("prefixItems", [])
    for index, item_rule in enumerate(prefix[: len(value)]):
        _validate(value[index], item_rule, root, f"{path}[{index}]", errors)
    item_rule = rule.get("items")
    if item_rule is not None:
        start = len(prefix) if prefix else 0
        for index in range(start, len(value)):
            _validate(value[index], item_rule, root, f"{path}[{index}]", errors)


def _matches(value, rule, root, path):
    branch_errors: list[str] = []
    _validate(value, rule, root, path, branch_errors)
    return not branch_errors


def _resolve_reference(root, reference):
    if not isinstance(reference, str) or not reference.startswith("#/"):
        raise SchemaValidationError(f"unsupported schema reference: {reference!r}")
    value: Any = root
    for token in reference[2:].split("/"):
        value = value[token.replace("~1", "/").replace("~0", "~")]
    return value


def _is_type(value, expected):
    if isinstance(expected, list):
        return any(_is_type(value, item) for item in expected)
    return {
        "object": lambda: isinstance(value, dict),
        "array": lambda: isinstance(value, list),
        "string": lambda: isinstance(value, str),
        "boolean": lambda: isinstance(value, bool),
        "null": lambda: value is None,
        "integer": lambda: _is_number(value) and float(value).is_integer(),
        "number": lambda: _is_number(value),
    }.get(expected, lambda: False)()


def _is_number(value):
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and (not isinstance(value, float) or math.isfinite(value))
    )


def _json_equal(left: Any, right: Any) -> bool:
    """Compare JSON values using JSON Schema's mathematical number equality."""
    if _is_number(left) and _is_number(right):
        return left == right
    if isinstance(left, bool) or isinstance(right, bool):
        return isinstance(left, bool) and isinstance(right, bool) and left == right
    if left is None or right is None:
        return left is None and right is None
    if isinstance(left, str) or isinstance(right, str):
        return isinstance(left, str) and isinstance(right, str) and left == right
    if isinstance(left, list) or isinstance(right, list):
        return (
            isinstance(left, list)
            and isinstance(right, list)
            and len(left) == len(right)
            and all(_json_equal(a, b) for a, b in zip(left, right))
        )
    if isinstance(left, dict) or isinstance(right, dict):
        return (
            isinstance(left, dict)
            and isinstance(right, dict)
            and left.keys() == right.keys()
            and all(_json_equal(left[key], right[key]) for key in left)
        )
    return type(left) is type(right) and left == right


def unsupported_schema_keywords(schema: Any) -> list[str]:
    """Return validation keywords used by a schema but not implemented here."""
    found: set[str] = set()
    _collect_schema_keywords(schema, found)
    return sorted(found - SUPPORTED_SCHEMA_KEYWORDS)


def _collect_schema_keywords(schema: Any, found: set[str]) -> None:
    if not isinstance(schema, dict):
        return
    found.update(schema)
    for keyword, value in schema.items():
        if keyword in {"properties", "$defs"} and isinstance(value, dict):
            for child in value.values():
                _collect_schema_keywords(child, found)
        elif keyword in {"allOf", "anyOf", "oneOf", "prefixItems"} and isinstance(value, list):
            for child in value:
                _collect_schema_keywords(child, found)
        elif keyword in {
            "additionalProperties", "contains", "else", "if", "items", "not",
            "propertyNames", "then",
        }:
            _collect_schema_keywords(value, found)
