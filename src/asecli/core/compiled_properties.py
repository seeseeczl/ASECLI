"""Conservative ShaderLab ``Properties`` parser for presentation reconciliation."""

from __future__ import annotations

import re


_PROPERTIES_TOKEN = re.compile(r"(?m)^[ \t]*Properties\b")
_ATTRIBUTE_TOKEN = re.compile(r"\[[^\]\r\n]*\]")
_ATTRIBUTES_ONLY = re.compile(r"^(?:\[[^\]\r\n]*\][ \t]*)+$")
_PROPERTY_DECLARATION = re.compile(
    r"^(?P<attributes>(?:\[[^\]\r\n]*\][ \t]*)*)"
    r"(?P<name>[A-Za-z_][A-Za-z0-9_]*)[ \t]*\([ \t]*"
    r'"(?P<display_name>(?:\\.|[^"\\])*)"[ \t]*,'
)
_ATTRIBUTE_DETAIL = re.compile(
    r"^\[(?P<type>[A-Za-z_][A-Za-z0-9_]*)(?:\((?P<args>.*)\))?\]$"
)


def parse_compiled_properties(source: str) -> list[dict]:
    """Parse one ShaderLab Properties block or fail on an unknown active line.

    ASECLI only promises layouts produced by its verified ASE profile. Failing
    closed is intentional: an unparsed declaration must never become a vacuous
    presentation pass.
    """
    body = _properties_body(source)
    if body is None:
        return []

    properties: list[dict] = []
    pending_attributes: list[str] = []
    in_block_comment = False
    for line_number, raw_line in enumerate(body.splitlines(), start=1):
        line, in_block_comment = _without_comments(raw_line, in_block_comment)
        stripped = line.strip()
        if not stripped:
            continue
        if _ATTRIBUTES_ONLY.fullmatch(stripped):
            pending_attributes.extend(_ATTRIBUTE_TOKEN.findall(stripped))
            continue
        match = _PROPERTY_DECLARATION.match(stripped)
        if match is None:
            raise ValueError(
                f"unrecognized ShaderLab Properties declaration at block line {line_number}: {stripped!r}"
            )
        raw_attributes = [
            *pending_attributes,
            *_ATTRIBUTE_TOKEN.findall(match.group("attributes")),
        ]
        pending_attributes.clear()
        attributes = [_parse_attribute(raw) for raw in raw_attributes]
        properties.append(
            {
                "property_name": match.group("name"),
                "display_name": match.group("display_name"),
                "attributes": attributes,
                "hidden": any(
                    item["type"].lower() == "hideininspector" for item in attributes
                ),
                "block_line": line_number,
            }
        )
    if in_block_comment:
        raise ValueError("unterminated block comment in ShaderLab Properties block")
    if pending_attributes:
        raise ValueError("ShaderLab property attributes are not followed by a declaration")
    return properties


def inspect_compiled_properties(source: str) -> tuple[list[dict], str | None]:
    try:
        return parse_compiled_properties(source), None
    except ValueError as exc:
        return [], str(exc)


def _properties_body(source: str) -> str | None:
    matches = list(_PROPERTIES_TOKEN.finditer(source))
    if not matches:
        return None
    if len(matches) != 1:
        raise ValueError(f"expected at most one ShaderLab Properties block, found {len(matches)}")
    token = matches[0]
    opening = re.match(r"[ \t\r\n]*\{", source[token.end() :])
    if opening is None:
        raise ValueError("ShaderLab Properties keyword is not followed by an opening brace")
    open_index = token.end() + opening.end() - 1
    depth = 1
    in_string = False
    in_line_comment = False
    in_block_comment = False
    escaped = False
    index = open_index + 1
    while index < len(source):
        char = source[index]
        next_char = source[index + 1] if index + 1 < len(source) else ""
        if in_line_comment:
            if char in "\r\n":
                in_line_comment = False
            index += 1
            continue
        if in_block_comment:
            if char == "*" and next_char == "/":
                in_block_comment = False
                index += 2
            else:
                index += 1
            continue
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            index += 1
            continue
        if char == "/" and next_char == "/":
            in_line_comment = True
            index += 2
            continue
        if char == "/" and next_char == "*":
            in_block_comment = True
            index += 2
            continue
        if char == '"':
            in_string = True
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return source[open_index + 1 : index]
        index += 1
    raise ValueError("unterminated ShaderLab Properties block")


def _without_comments(line: str, in_block_comment: bool) -> tuple[str, bool]:
    result: list[str] = []
    in_string = False
    escaped = False
    index = 0
    while index < len(line):
        char = line[index]
        next_char = line[index + 1] if index + 1 < len(line) else ""
        if in_block_comment:
            if char == "*" and next_char == "/":
                in_block_comment = False
                index += 2
            else:
                index += 1
            continue
        if in_string:
            result.append(char)
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            index += 1
            continue
        if char == '"':
            in_string = True
            result.append(char)
            index += 1
            continue
        if char == "/" and next_char == "/":
            break
        if char == "/" and next_char == "*":
            in_block_comment = True
            index += 2
            continue
        result.append(char)
        index += 1
    return "".join(result), in_block_comment


def _parse_attribute(raw: str) -> dict:
    match = _ATTRIBUTE_DETAIL.fullmatch(raw)
    if match is None:
        raise ValueError(f"invalid ShaderLab property attribute: {raw!r}")
    result = {"type": match.group("type"), "raw": raw, "args": match.group("args")}
    if result["type"] in {"ASECLITooltip", "ASECLIHelpBox", "TooltipMzgui", "HelpBoxMzgui"} and result["args"] is not None:
        units = re.findall(r"#([0-9A-Fa-f]{4})", result["args"])
        encoded = b"".join(int(unit, 16).to_bytes(2, "little") for unit in units)
        result["text"] = encoded.decode("utf-16-le", errors="replace")
    return result
