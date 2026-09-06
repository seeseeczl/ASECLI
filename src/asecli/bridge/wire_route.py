"""Apply a fixed WireNode routing plan through the currently installed ASE API."""

from __future__ import annotations

import base64
import json
from pathlib import Path

from .mcp_client import McpClient, McpError
from .editor_create import _execute_code_result_text
from .recompile import _detect_project_root
from .resource_text import compose_resource_text

WIRE_ROUTE_SNIPPET = compose_resource_text(
    "asecli.bridge", "resources", ("wire_route.transaction.cs.txt",),
)
_RESULT_MARKER = "ASECLI_WIRE_ROUTE_V1:"


def apply_wire_routes_via_mcp(
    shader_path: str | Path,
    changes: tuple[dict, ...],
    *,
    mcp_url: str = "http://127.0.0.1:8080/mcp",
    instance_token: str | None = None,
    unity_instance: str | None = None,
    allow_remote_mcp: bool = False,
) -> dict:
    target = Path(shader_path).resolve()
    if not target.is_file():
        raise FileNotFoundError(shader_path)
    root = _detect_project_root(target)
    asset_path = target.as_posix().removeprefix(root.as_posix() + "/")
    routes = _validated_routes(changes)
    payload = {"version": 1, "asset_path": asset_path, "routes": routes}
    encoded = base64.b64encode(
        json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    ).decode("ascii")
    code = WIRE_ROUTE_SNIPPET.replace("{payload_base64}", encoded)
    client = McpClient(mcp_url, instance_token=instance_token, allow_remote=allow_remote_mcp)
    client.connect()
    arguments = {"action": "execute", "code": code}
    if unity_instance is not None:
        arguments["unity_instance"] = unity_instance
    result = client.call_tool("execute_code", arguments)
    response = _parse_result(_execute_code_result_text(result, instance_token))
    if response.get("protocol") != "ASECLI_WIRE_ROUTE_V1":
        raise McpError("WireNode route protocol version is missing or unsupported")
    if response.get("asset_path") != asset_path:
        raise McpError("WireNode route returned a different asset path")
    if response.get("saved") is not True:
        raise McpError("WireNode route did not confirm saved=True")
    if response.get("applied_routes") != len(routes):
        raise McpError("WireNode route applied-count does not match the plan")
    created = response.get("created_node_ids")
    expected_created = sum(len(item["anchors"]) for item in routes if item["action"] == "add")
    if not isinstance(created, list) or len(created) != expected_created:
        raise McpError("WireNode route returned an invalid created-node manifest")
    return response


def _validated_routes(changes: tuple[dict, ...]) -> list[dict]:
    routes = []
    seen = set()
    for change in changes:
        action = change.get("action")
        logical = change.get("logical_wire")
        if action not in {"move", "add"} or not isinstance(logical, dict):
            raise ValueError("invalid WireNode route change")
        normalized = {}
        for source, target in (
            ("from_node", "from_node"), ("from_port", "from_port"),
            ("to_node", "to_node"), ("to_port", "to_port"),
        ):
            value = str(logical.get(source, ""))
            if not value.lstrip("-").isdigit():
                raise ValueError(f"WireNode route {source} must be numeric")
            normalized[target] = int(value)
        key = tuple(normalized.values())
        if key in seen:
            raise ValueError("duplicate WireNode logical route")
        seen.add(key)
        if action == "add":
            anchors = change.get("anchors")
            if not isinstance(anchors, list) or not 1 <= len(anchors) <= 2:
                raise ValueError("a logical wire may add one or two WireNode anchors")
            normalized_anchors = [_point(item) for item in anchors]
        else:
            anchors = change.get("anchors")
            if not isinstance(anchors, list) or not anchors:
                raise ValueError("WireNode move requires at least one existing anchor")
            normalized_anchors = []
            ids = set()
            for item in anchors:
                node_id = str(item.get("wire_node_id", ""))
                if not node_id.lstrip("-").isdigit() or node_id in ids:
                    raise ValueError("WireNode move ids must be unique numeric values")
                ids.add(node_id)
                normalized_anchors.append({"wire_node_id": int(node_id), "to": _point(item.get("to"))})
        routes.append({"action": action, "logical_wire": normalized, "anchors": normalized_anchors})
    return routes


def _point(value) -> list[float]:
    if not isinstance(value, (list, tuple)) or len(value) != 2:
        raise ValueError("WireNode anchor must be an x,y pair")
    try:
        point = [float(value[0]), float(value[1])]
    except (TypeError, ValueError) as exc:
        raise ValueError("WireNode anchor coordinates must be numeric") from exc
    if not all(abs(item) <= 10_000_000 for item in point):
        raise ValueError("WireNode anchor coordinate is outside the supported canvas range")
    return point


def _parse_result(text: str) -> dict:
    marker = text.find(_RESULT_MARKER)
    if marker < 0:
        raise McpError("MCP tool result did not contain the WireNode route marker")
    raw = text[marker + len(_RESULT_MARKER):].lstrip()
    try:
        value, _ = json.JSONDecoder().raw_decode(raw)
    except json.JSONDecodeError as exc:
        raise McpError("MCP tool returned malformed WireNode route JSON") from exc
    if not isinstance(value, dict):
        raise McpError("MCP WireNode route result must be a JSON object")
    return value
