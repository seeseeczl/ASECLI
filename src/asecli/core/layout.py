"""Node layout (FR-0008, ADR-0005): Sugiyama-lite layered arrangement.

Only mutates node position fields (raw_fields[3] = "x,y"). Everything else
is untouched, and the wire set is preserved by construction.
"""

from __future__ import annotations

from collections import defaultdict
import math

from .commentary import COMMENTARY_TYPE, inspect_comment_groups
from .local_vars import local_var_edges
from .model import AseGraph, NodeLine

MASTER_TYPES = {
    "AmplifyShaderEditor.TemplateMultiPassMasterNode",
    "AmplifyShaderEditor.TemplateMasterNode",
}


def layout_positions(
    graph: AseGraph,
    gap_x: float = 280.0,
    gap_y: float = 120.0,
    origin_x: float = -640.0,
    origin_y: float = 0.0,
) -> dict[str, tuple[float, float]]:
    """Compute tidy left-to-right positions. Deterministic for a given graph."""
    nodes = graph.nodes
    frozen = _commentary_composite_nodes(graph)
    movable_nodes = [node for node in nodes if node.node_id not in frozen]
    ids = [n.node_id for n in movable_nodes]
    id_set = set(ids)

    if frozen and movable_nodes:
        max_right = max(_node_right_edge(node, graph) for node in nodes if node.node_id in frozen)
        origin_x = max(origin_x, max_right + gap_x)

    # edges: out node feeds in node
    out_edges: dict[str, list[str]] = defaultdict(list)
    in_degree: dict[str, int] = {i: 0 for i in ids}
    edge_pairs = {
        (w.out_node, w.in_node)
        for w in graph.wires
        if w.out_node in id_set and w.in_node in id_set and w.out_node != w.in_node
    }
    edge_pairs.update(
        (source, target)
        for source, target in local_var_edges(graph)
        if source in id_set and target in id_set and source != target
    )
    for source, target in sorted(edge_pairs):
        out_edges[source].append(target)
        in_degree[target] += 1

    masters = {n.node_id for n in movable_nodes if n.type_name in MASTER_TYPES}
    non_master = [i for i in ids if i not in masters]

    # Kahn topological order with cycle tolerance
    layer: dict[str, int] = {}
    queue = [i for i in non_master if in_degree[i] == 0]
    for i in queue:
        layer[i] = 0
    order = list(queue)
    while order:
        cur = order.pop(0)
        for nxt in out_edges.get(cur, []):
            if nxt in masters:
                continue
            layer[nxt] = max(layer.get(nxt, 0), layer[cur] + 1)
            in_degree[nxt] -= 1
            if in_degree[nxt] == 0:
                order.append(nxt)
    # cycle survivors: place after their longest known predecessor
    unassigned = [i for i in non_master if i not in layer]
    changed = True
    while changed and unassigned:
        changed = False
        for i in list(unassigned):
            preds = [layer[p] for p, outs in out_edges.items() if i in outs and p in layer]
            if preds:
                layer[i] = max(preds) + 1
                unassigned.remove(i)
                changed = True
    for i in unassigned:  # fully isolated from everything known
        layer[i] = 0

    max_layer = max(layer.values(), default=-1)
    for m in masters:
        layer[m] = max_layer + 1 if non_master else 0
    if masters and non_master:
        max_layer += 1

    # barycenter ordering within layers (two passes), deterministic
    by_layer: dict[int, list[str]] = defaultdict(list)
    for n in movable_nodes:  # instruction order = stable initial order
        by_layer[layer[n.node_id]].append(n.node_id)
    preds_of: dict[str, list[str]] = defaultdict(list)
    for src, outs in out_edges.items():
        for dst in outs:
            preds_of[dst].append(src)

    y_of: dict[str, float] = {}
    for l in sorted(by_layer):
        for row, nid in enumerate(by_layer[l]):
            y_of[nid] = float(row)
    for _ in range(2):
        for l in sorted(by_layer):
            initial_row = {nid: i for i, nid in enumerate(by_layer[l])}
            def key(nid: str) -> tuple[float, int]:
                ps = [y_of[p] for p in preds_of.get(nid, []) if p in y_of]
                return (sum(ps) / len(ps) if ps else 0.0, initial_row[nid])
            by_layer[l].sort(key=key)
            for row, nid in enumerate(by_layer[l]):
                y_of[nid] = float(row)

    positions: dict[str, tuple[float, float]] = {}
    for l in sorted(by_layer):
        members = by_layer[l]
        rows = len(members)
        for row, nid in enumerate(members):
            x = origin_x + l * gap_x
            y = origin_y + (row - (rows - 1) / 2.0) * gap_y
            positions[nid] = (round(x, 1), round(y, 1))
    for node in nodes:
        if node.node_id in frozen:
            positions[node.node_id] = _position(node)
    return positions


def apply_positions(graph: AseGraph, positions: dict[str, tuple[float, float]]) -> int:
    """Write positions back into node raw_fields. Returns count of nodes moved."""
    moved = 0
    for n in graph.nodes:
        pos = positions.get(n.node_id)
        if pos is None:
            continue
        if _position(n) == pos:
            continue
        new_xy = f"{pos[0]},{pos[1]}"
        if n.raw_fields[3] != new_xy:
            n.raw_fields[3] = new_xy
            graph.replace_node(n)
            moved += 1
    return moved


def tidy(graph: AseGraph, gap_x: float = 280.0, gap_y: float = 120.0) -> int:
    return apply_positions(graph, layout_positions(graph, gap_x, gap_y))


def _commentary_composite_nodes(graph: AseGraph) -> set[str]:
    """Keep curated Comment frames and every member as fixed composite units."""
    frozen = set()
    for group in inspect_comment_groups(graph):
        frozen.add(group["node_id"])
        frozen.update(group["members"])
    return frozen


def _position(node: NodeLine) -> tuple[float, float]:
    try:
        x, y = node.raw_fields[3].split(",")
        position = float(x), float(y)
    except (IndexError, ValueError) as exc:
        raise ValueError(f"node {node.node_id} has invalid x,y position") from exc
    if not all(math.isfinite(value) for value in position):
        raise ValueError(f"node {node.node_id} has non-finite x,y position")
    return position


def _node_right_edge(node: NodeLine, graph: AseGraph) -> float:
    x, _ = _position(node)
    if node.type_name == COMMENTARY_TYPE:
        group = next(item for item in inspect_comment_groups(graph) if item["node_id"] == node.node_id)
        return x + group["width"]
    return x + 200.0
