"""Conservative purpose-title inference for existing ASE Comment frames."""

from __future__ import annotations

import re
from typing import Mapping, Protocol

from .commentary import inspect_comment_groups, parse_commentary_node
from .local_vars import REGISTER_LOCAL_VAR_TYPE, parse_register_local_var
from .model import AseGraph

_PLACEHOLDER_TITLE = re.compile(
    r"^(?:comment|group|组|处理\s*\d*|临时(?:组)?\s*\d*)$", re.IGNORECASE,
)


class Geometry(Protocol):
    node_title: str
    input_port_labels: dict[str, str] | None


def govern_comment_purposes(
    graph: AseGraph,
    geometry: Mapping[str, Geometry],
    *,
    apply: bool,
) -> list[dict]:
    """Preserve meaningful titles and infer only missing algorithm purposes."""
    groups = {group["node_id"]: group for group in inspect_comment_groups(graph)}

    def leaf_members(group_id: str, visiting: set[str] | None = None) -> set[str]:
        visiting = set() if visiting is None else visiting
        if group_id in visiting:
            raise ValueError(f"comment membership contains a cycle at node {group_id}")
        visiting.add(group_id)
        result = set()
        for member in groups[group_id]["members"]:
            if member in groups:
                result.update(leaf_members(member, visiting))
            else:
                result.add(member)
        visiting.remove(group_id)
        return result

    results = []
    for group_id in sorted(groups, key=_id_key):
        group = groups[group_id]
        title = group["title"].strip()
        if title and not _PLACEHOLDER_TITLE.fullmatch(title):
            results.append({"comment_id": group_id, "status": "existing", "title": title})
            continue
        suggestion, source = _infer_comment_title(graph, geometry, leaf_members(group_id))
        if suggestion is None:
            results.append({
                "comment_id": group_id,
                "status": "unresolved",
                "title": group["title"],
                "reason": "no_unique_register_consumer_or_algorithm_sink",
            })
            continue
        results.append({
            "comment_id": group_id,
            "status": "inferred",
            "title": group["title"],
            "suggested_title": suggestion,
            "source": source,
        })
        if apply:
            node = graph.node_by_id(group_id)
            if node is None:
                raise ValueError(f"comment node {group_id} not found")
            count = int(node.raw_fields[9])
            node.raw_fields[10 + count] = suggestion
            graph.replace_node(node)
            groups[group_id] = parse_commentary_node(node)
    return results


def _infer_comment_title(graph: AseGraph, geometry, members: set[str]):
    registers = []
    for member in sorted(members, key=_id_key):
        node = graph.node_by_id(member)
        if node is not None and node.type_name == REGISTER_LOCAL_VAR_TYPE:
            try:
                name = parse_register_local_var(node)["name"].strip()
            except ValueError:
                continue
            if name:
                registers.append(name)
    if len(registers) == 1:
        return _safe_title(f"生成 {registers[0]}"), "register_local_var"

    outgoing = [
        wire for wire in graph.wires
        if wire.out_node in members and wire.in_node not in members
    ]
    consumers = {(wire.in_node, wire.in_port) for wire in outgoing}
    if len(consumers) == 1:
        consumer_id, in_port = next(iter(consumers))
        consumer = _node_label(graph, geometry, consumer_id)
        labels = getattr(geometry.get(consumer_id), "input_port_labels", {}) or {}
        port_label = str(labels.get(in_port, "")).strip()
        if _meaningful_label(consumer):
            if _meaningful_label(port_label):
                return _safe_title(f"为「{consumer}」计算「{port_label}」"), "external_consumer_port"
            return _safe_title(f"为「{consumer}」计算输入"), "external_consumer"

    internal_sources = {
        wire.out_node for wire in graph.wires
        if wire.out_node in members and wire.in_node in members
    }
    sinks = sorted(members - internal_sources, key=_id_key)
    real_sinks = [item for item in sinks if _meaningful_label(_node_label(graph, geometry, item))]
    if len(real_sinks) == 1:
        return _safe_title(f"计算「{_node_label(graph, geometry, real_sinks[0])}」"), "local_algorithm_sink"
    return None, None


def _node_label(graph, geometry, node_id: str) -> str:
    title = str(getattr(geometry.get(node_id), "node_title", "") or "").strip()
    if title:
        return title
    node = graph.node_by_id(node_id)
    if node is None:
        return ""
    return re.sub(r"Node$", "", node.type_name.rsplit(".", 1)[-1]).strip()


def _meaningful_label(value: str) -> bool:
    return bool(value.strip()) and value.strip().lower() not in {
        "node", "input", "output", "function", "property", "comment", "group",
    }


def _safe_title(value: str) -> str:
    return value.replace(";", "，").replace("\r", " ").replace("\n", " ")[:4096]


def _id_key(value: str):
    return (0, int(value)) if value.lstrip("-").isdigit() else (1, value)
