"""Conservative graph-liveness and external material-property usage audit."""

from __future__ import annotations

from collections import defaultdict, deque
from pathlib import Path
import re

from ..core import AseGraph, NodeLine, is_material_property_node, local_var_edges


COMMENTARY_TYPE = "AmplifyShaderEditor.CommentaryNode"
MASTER_TYPES = {
    "AmplifyShaderEditor.TemplateMultiPassMasterNode",
    "AmplifyShaderEditor.TemplateMasterNode",
    "AmplifyShaderEditor.StandardSurfaceOutputNode",
    "AmplifyShaderEditor.FunctionOutput",
    "AmplifyShaderEditor.FunctionOutputNode",
}
SOURCE_SUFFIXES = {".cs", ".cginc", ".hlsl", ".compute", ".shader"}
MAX_SCAN_BYTES = 8 * 1024 * 1024


def live_node_ids(graph: AseGraph) -> set[str]:
    """Return nodes that contribute to an output through wires or Local Vars."""
    reverse: dict[str, set[str]] = defaultdict(set)
    for wire in graph.wires:
        reverse[wire.in_node].add(wire.out_node)
    for source, target in local_var_edges(graph):
        reverse[target].add(source)

    masters = [node for node in graph.nodes if node.type_name in MASTER_TYPES]
    active = [
        node.node_id
        for node in masters
        if len(node.raw_fields) > 6 and node.raw_fields[6].lower() == "true"
    ]
    sinks = active or [node.node_id for node in masters]
    live = set(sinks)
    queue = deque(sinks)
    while queue:
        node_id = queue.popleft()
        for source in reverse.get(node_id, ()):
            if source in live:
                continue
            live.add(source)
            queue.append(source)
    return live


def usage_audit(shader_path: str, graph: AseGraph) -> dict:
    """Classify dead-graph candidates without calling externally used properties unused."""
    live = live_node_ids(graph)
    connected = {
        node_id
        for wire in graph.wires
        for node_id in (wire.out_node, wire.in_node)
    }
    semantic = {node_id for edge in local_var_edges(graph) for node_id in edge}
    project_root = _detect_project_root(Path(shader_path).resolve())
    unused: list[dict] = []
    external: list[dict] = []
    for node in graph.nodes:
        if node.node_id in live or node.type_name == COMMENTARY_TYPE or node.type_name in MASTER_TYPES:
            continue
        item = {
            "node_id": node.node_id,
            "node_type": node.type_name,
            "position": node.raw_fields[3] if len(node.raw_fields) > 3 else None,
            "reason": "not_reachable_from_graph_output",
            "has_wire_or_local_var_relation": node.node_id in connected or node.node_id in semantic,
        }
        if is_material_property_node(node):
            property_name = node.raw_fields[7]
            item["property_name"] = property_name
            refs = find_external_references(project_root, Path(shader_path).resolve(), property_name)
            if refs:
                item["classification"] = "external_consumer"
                item["external_references"] = refs
                external.append(item)
                continue
        item["classification"] = "unused_candidate"
        unused.append(item)
    return {
        "live_node_count": len(live),
        "live_node_ids": sorted(live, key=_node_id_sort_key),
        "unused_candidates": sorted(unused, key=lambda item: _node_id_sort_key(item["node_id"])),
        "external_consumers": sorted(external, key=lambda item: _node_id_sort_key(item["node_id"])),
        "policy": (
            "unused_candidates are conservative review targets; external_consumers must not be pruned "
            "only because they have no ASE wire"
        ),
    }


def external_references_for_node(shader_path: str, node: NodeLine) -> list[dict]:
    if not is_material_property_node(node):
        return []
    path = Path(shader_path).resolve()
    return find_external_references(_detect_project_root(path), path, node.raw_fields[7])


def find_external_references(project_root: Path, shader_path: Path, token: str) -> list[dict]:
    pattern = re.compile(rf"(?<![A-Za-z0-9_]){re.escape(token)}(?![A-Za-z0-9_])")
    results: list[dict] = []
    assets = project_root / "Assets"
    for path in sorted(assets.rglob("*")):
        if not path.is_file() or path.is_symlink() or path.resolve() == shader_path:
            continue
        if path.suffix.lower() not in SOURCE_SUFFIXES or path.name.endswith(".shader.bak"):
            continue
        try:
            if path.stat().st_size > MAX_SCAN_BYTES:
                continue
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for line_number, line in enumerate(text.splitlines(), 1):
            if pattern.search(line):
                results.append(
                    {
                        "path": path.relative_to(project_root).as_posix(),
                        "line": line_number,
                    }
                )
                if len(results) >= 100:
                    return results
    return results


def _detect_project_root(path: Path) -> Path:
    cur = path.parent
    while cur != cur.parent:
        if (cur / "Assets").is_dir() and (cur / "ProjectSettings").is_dir():
            return cur
        cur = cur.parent
    raise ValueError(f"cannot locate Unity project root for {path}")


def _node_id_sort_key(value: str) -> tuple[int, int | str]:
    return (0, int(value)) if value.lstrip("-").isdigit() else (1, value)
