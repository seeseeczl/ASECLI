"""Recognize the certified single-assignment AlphaModulate HLSL subset."""

from __future__ import annotations

import re


def inputs(function: dict | None) -> tuple[str, str] | None:
    if not function or function.get("source") != "String":
        return None
    ports = function.get("ports", [])
    outputs = [port for port in ports if port.get("direction") == "Output"]
    if len(outputs) != 1 or outputs[0].get("type") != "Vector3":
        return None
    output_name = outputs[0].get("name")
    if not isinstance(output_name, str) or not re.fullmatch(r"[A-Za-z_]\w*", output_name):
        return None
    body = _strip_comments(function.get("body", ""))
    if body is None:
        return None
    match = re.fullmatch(
        rf"\s*{re.escape(output_name)}\s*=\s*lerp\s*\((.*)\)\s*;\s*",
        body,
        flags=re.DOTALL,
    )
    if not match:
        return None
    args = _split_arguments(match.group(1))
    if len(args) != 3 or not _is_white(args[0]):
        return None
    color_name, alpha_name = args[1].strip(), args[2].strip()
    if not re.fullmatch(r"[A-Za-z_]\w*", color_name):
        return None
    if not re.fullmatch(r"[A-Za-z_]\w*", alpha_name):
        return None
    input_types = {
        port.get("name"): port.get("type")
        for port in ports if port.get("direction") == "Input"
    }
    if input_types.get(color_name) != "Vector3" or input_types.get(alpha_name) != "Vector1":
        return None
    return color_name, alpha_name


def _split_arguments(value: str) -> list[str]:
    result, start, depth = [], 0, 0
    for index, char in enumerate(value):
        if char == "(":
            depth += 1
        elif char == ")":
            depth -= 1
            if depth < 0:
                return []
        elif char == "," and depth == 0:
            result.append(value[start:index])
            start = index + 1
    if depth != 0:
        return []
    result.append(value[start:])
    return result


def _is_white(value: str) -> bool:
    compact = re.sub(r"\s+", "", value)
    constructor = re.fullmatch(r"(?:float|half)3\((.*)\)", compact, flags=re.IGNORECASE)
    if constructor:
        parts = _split_arguments(constructor.group(1))
        return len(parts) == 3 and all(_is_one(part) for part in parts)
    scalar = re.fullmatch(r"\(?([^()]+)\)?\.xxx", compact, flags=re.IGNORECASE)
    return bool(scalar and _is_one(scalar.group(1)))


def _is_one(value: str) -> bool:
    try:
        return float(value.rstrip("fF")) == 1.0
    except ValueError:
        return False


def _strip_comments(value: str) -> str | None:
    result, index, state = [], 0, "code"
    while index < len(value):
        char = value[index]
        following = value[index + 1] if index + 1 < len(value) else ""
        if state == "code":
            if char == '"':
                state = "string"
                result.append(char)
            elif char == "/" and following in {"/", "*"}:
                result.extend("  ")
                index += 1
                state = "line_comment" if following == "/" else "block_comment"
            else:
                result.append(char)
        elif state == "string":
            result.append(char)
            if char == "\\" and following:
                result.append(following)
                index += 1
            elif char == '"':
                state = "code"
        elif state == "line_comment":
            result.append(char if char in "\r\n" else " ")
            if char in "\r\n":
                state = "code"
        elif char == "*" and following == "/":
            result.extend("  ")
            index += 1
            state = "code"
        else:
            result.append(char if char in "\r\n" else " ")
        index += 1
    return None if state in {"string", "block_comment"} else "".join(result)
