"""Parser for backward-compatible ASECLI graph geometry payloads."""

from __future__ import annotations

import base64
import math

from .mcp_client import McpError


def parse_geometry_payload(payload: str, geometry_type):
    version = payload.splitlines()[0]
    nodes: dict[str, dict] = {}
    ports: list[tuple[str, str, str, float, float, str]] = []
    for row in payload.splitlines()[1:]:
        parts = row.split("|")
        if parts[0] == "N" and len(parts) in {7, 8}:
            try:
                values = [float(value) for value in parts[2:7]]
            except ValueError as exc:
                raise McpError("MCP graph-geometry result contains non-numeric node geometry") from exc
            if (
                parts[1] in nodes
                or not all(math.isfinite(value) for value in values)
                or min(values[2:]) <= 0
            ):
                raise McpError(f"MCP graph-geometry result contains invalid node geometry for {parts[1]}")
            node_title = ""
            if len(parts) == 8 and version == "ASECLI_GEOMETRY_V3":
                try:
                    node_title = base64.b64decode(parts[7]).decode("utf-8")
                except Exception as exc:
                    raise McpError("MCP graph-geometry result contains malformed node title") from exc
            nodes[parts[1]] = dict(
                x=values[0], y=values[1], width=values[2], height=values[3],
                title_height=values[4], input_ports={}, output_ports={},
                node_title=node_title, input_port_labels={}, output_port_labels={},
            )
        elif parts[0] in {"I", "O"} and len(parts) in {5, 6}:
            try:
                label = ""
                if len(parts) == 6 and version == "ASECLI_GEOMETRY_V3":
                    label = base64.b64decode(parts[5]).decode("utf-8")
                ports.append((parts[0], parts[1], parts[2], float(parts[3]), float(parts[4]), label))
            except ValueError as exc:
                raise McpError("MCP graph-geometry result contains non-numeric port geometry") from exc
            except Exception as exc:
                raise McpError("MCP graph-geometry result contains malformed port label") from exc
        elif row:
            raise McpError("MCP graph-geometry result contains a malformed row")
    for direction, node_id, port_id, x, y, label in ports:
        if not math.isfinite(x) or not math.isfinite(y):
            raise McpError("MCP graph-geometry result contains non-finite port geometry")
        if node_id not in nodes:
            raise McpError(f"MCP graph-geometry port references missing node {node_id}")
        key = "input_ports" if direction == "I" else "output_ports"
        if port_id in nodes[node_id][key]:
            raise McpError(f"MCP graph-geometry result contains duplicate port {node_id}:{port_id}")
        nodes[node_id][key][port_id] = (x - nodes[node_id]["x"], y - nodes[node_id]["y"])
        label_key = "input_port_labels" if direction == "I" else "output_port_labels"
        nodes[node_id][label_key][port_id] = label
    if not nodes:
        raise McpError("MCP graph-geometry result is empty")
    return {node_id: geometry_type(**values) for node_id, values in nodes.items()}
