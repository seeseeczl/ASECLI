"""ShaderLab and standard URP Shader Graph blend-state semantics."""

from __future__ import annotations

import re


_BLEND_FACTORS = {
    value.lower(): value
    for value in (
        "Zero", "One", "SrcColor", "OneMinusSrcColor", "SrcAlpha",
        "OneMinusSrcAlpha", "DstColor", "OneMinusDstColor", "DstAlpha",
        "OneMinusDstAlpha", "SrcAlphaSaturate",
    )
}


def record_pass_blend(semantics: dict, target: dict, source_text: str | None) -> None:
    evidence = forward_blend_evidence(source_text or "")
    source = evidence.get("blend")
    target_blend = target_blend_factors(target)
    semantics["source_pass_blend"] = source
    semantics["target_pass_blend"] = target_blend
    semantics["pass_blend_parser"] = {
        key: value for key, value in evidence.items() if key != "blend"
    }
    if source is not None and target_blend is not None:
        semantics["rgb_blend_equivalent"] = source["rgb"] == target_blend["rgb"]
        semantics["alpha_blend_equivalent"] = source["alpha"] == target_blend["alpha"]


def forward_blend(source_text: str) -> dict | None:
    """Return the unique Forward pass blend factors, or None when unproved."""
    return forward_blend_evidence(source_text).get("blend")


def forward_blend_evidence(source_text: str) -> dict:
    """Parse a unique Forward Pass without trusting comments or unrelated text."""
    masked, error = _mask_comments(source_text)
    if error:
        return _evidence("malformed", 0, error)
    bodies, error = _pass_bodies(masked)
    if error:
        return _evidence("malformed", 0, error)
    search_bodies = bodies or [masked]
    forward = [body for body in search_bodies if _is_forward(body)]
    if not forward:
        return _evidence("missing", 0, "no Forward pass was found")
    if len(forward) != 1:
        return _evidence(
            "ambiguous", len(forward), f"expected one Forward pass, found {len(forward)}"
        )
    blend, status, reason, directive_count = _blend_in_pass(forward[0])
    result = _evidence(status, 1, reason)
    result["directive_count"] = directive_count
    if blend is not None:
        result["blend"] = blend
    return result


def target_blend_factors(target: dict) -> dict | None:
    if target.get("surface") != "Transparent":
        return {"rgb": ["One", "Zero"], "alpha": ["One", "Zero"]}
    return {
        "Alpha": {"rgb": ["SrcAlpha", "OneMinusSrcAlpha"], "alpha": ["One", "OneMinusSrcAlpha"]},
        "Premultiply": {"rgb": ["One", "OneMinusSrcAlpha"], "alpha": ["One", "OneMinusSrcAlpha"]},
        "Additive": {"rgb": ["SrcAlpha", "One"], "alpha": ["One", "One"]},
        "Multiply": {"rgb": ["DstColor", "Zero"], "alpha": ["Zero", "One"]},
        "MultiplySourceAlpha": {
            "rgb": ["DstColor", "Zero"],
            "alpha": ["One", "Zero"],
        },
    }.get(target.get("blend"))


def _evidence(status: str, count: int, reason: str) -> dict:
    return {
        "status": status,
        "candidate_count": count,
        "reason": reason,
        "parser_version": 2,
    }


def _mask_comments(source: str) -> tuple[str, str | None]:
    """Replace comments with spaces while preserving offsets, strings and newlines."""
    chars = list(source)
    index, state = 0, "code"
    while index < len(source):
        char = source[index]
        following = source[index + 1] if index + 1 < len(source) else ""
        if state == "code":
            if char == '"':
                state = "string"
            elif char == "/" and following == "/":
                chars[index] = chars[index + 1] = " "
                index += 1
                state = "line_comment"
            elif char == "/" and following == "*":
                chars[index] = chars[index + 1] = " "
                index += 1
                state = "block_comment"
        elif state == "string":
            if char == "\\" and following:
                index += 1
            elif char == '"':
                state = "code"
        elif state == "line_comment":
            if char in "\r\n":
                state = "code"
            else:
                chars[index] = " "
        else:
            if char == "*" and following == "/":
                chars[index] = chars[index + 1] = " "
                index += 1
                state = "code"
            elif char not in "\r\n":
                chars[index] = " "
        index += 1
    if state == "block_comment":
        return "".join(chars), "unterminated block comment"
    if state == "string":
        return "".join(chars), "unterminated string literal"
    return "".join(chars), None


def _mask_strings(source: str) -> str:
    chars = list(source)
    index, quoted = 0, False
    while index < len(source):
        char = source[index]
        if not quoted and char == '"':
            chars[index] = " "
            quoted = True
        elif quoted:
            if char == "\\" and index + 1 < len(source):
                chars[index] = chars[index + 1] = " "
                index += 1
            else:
                if char == '"':
                    quoted = False
                if char not in "\r\n":
                    chars[index] = " "
        index += 1
    return "".join(chars)


def _pass_bodies(source: str) -> tuple[list[str], str | None]:
    structural = _mask_strings(source)
    result, covered_until = [], -1
    for match in re.finditer(r"\bPass\s*\{", structural, flags=re.IGNORECASE):
        if match.start() < covered_until:
            continue
        opening = structural.find("{", match.start(), match.end())
        depth = 0
        for index in range(opening, len(structural)):
            if structural[index] == "{":
                depth += 1
            elif structural[index] == "}":
                depth -= 1
                if depth == 0:
                    result.append(source[opening + 1:index])
                    covered_until = index + 1
                    break
        else:
            return [], "unterminated Pass block"
    return result, None


def _is_forward(body: str) -> bool:
    header = re.split(r"\b(?:HLSLPROGRAM|CGPROGRAM)\b", body, maxsplit=1, flags=re.IGNORECASE)[0]
    return bool(re.search(r'\bName\s+"Forward"(?!\w)', header, flags=re.IGNORECASE))


def _blend_in_pass(body: str) -> tuple[dict | None, str, str, int]:
    header = re.split(r"\b(?:HLSLPROGRAM|CGPROGRAM)\b", body, maxsplit=1, flags=re.IGNORECASE)[0]
    directives = re.findall(r"(?im)^\s*Blend\s+(.+?)\s*$", header)
    if len(directives) > 1:
        return None, "ambiguous", f"expected at most one Blend directive, found {len(directives)}", len(directives)
    if not directives:
        if re.search(r"\bBlend\b", header, flags=re.IGNORECASE):
            return None, "unsupported", "Blend directive is not on a uniquely parseable line", 1
        return _off_blend(), "parsed", "Forward pass uses implicit Blend Off", 0
    value = directives[0].strip()
    if value.lower() == "off":
        return _off_blend(), "parsed", "Forward pass explicitly uses Blend Off", 1
    channels = [part.strip().split() for part in value.split(",")]
    if len(channels) not in (1, 2) or any(len(part) != 2 for part in channels):
        return None, "unsupported", f"unsupported Blend directive: {value}", 1
    normalized = []
    for source, destination in channels:
        pair = (_BLEND_FACTORS.get(source.lower()), _BLEND_FACTORS.get(destination.lower()))
        if None in pair:
            return None, "unsupported", f"unsupported Blend factors: {value}", 1
        normalized.append(list(pair))
    return {
        "rgb": normalized[0],
        "alpha": normalized[1] if len(normalized) == 2 else list(normalized[0]),
    }, "parsed", "unique Forward pass Blend parsed", 1


def _off_blend() -> dict:
    return {"rgb": ["One", "Zero"], "alpha": ["One", "Zero"]}
