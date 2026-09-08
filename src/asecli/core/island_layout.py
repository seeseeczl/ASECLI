"""Pack physical calculation islands without changing their internal fishbones."""

from collections import defaultdict
from math import isfinite

from .commentary import COMMENTARY_TYPE, inspect_comment_groups
from .layout import MASTER_TYPES
from .layout_graph import node_rect
from .local_vars import local_var_edges, REGISTER_LOCAL_VAR_TYPE, parse_register_local_var
from .wire_router import WIRE_NODE_TYPE


def pack_calculation_islands(graph, geometry, positions, *, columns=3, gap=96.0):
    if isinstance(columns, bool) or not isinstance(columns, int) or not 1 <= columns <= 8:
        raise ValueError('island columns must be an integer from 1 to 8')
    if not isfinite(gap) or gap < 96:
        raise ValueError('island gap must be at least 96px')
    nodes = {n.node_id: n for n in graph.nodes}
    ids = set(positions) - {n.node_id for n in nodes.values() if n.type_name == COMMENTARY_TYPE}
    if any(nodes[i].type_name == WIRE_NODE_TYPE for i in ids):
        raise ValueError('island packing with fixed WireNodes requires a separately authorized routing workflow')
    for i in ids:
        if i not in geometry or not all(isfinite(v) for v in (*positions[i], geometry[i].width, geometry[i].height)):
            raise ValueError(f'missing or nonfinite island geometry: {i}')
        if geometry[i].width <= 0 or geometry[i].height <= 0:
            raise ValueError(f'empty island geometry: {i}')
    parent = {i: i for i in ids}

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    def union(a, b):
        parent[find(a)] = find(b)

    for wire in graph.wires:
        if wire.out_node in ids and wire.in_node in ids:
            union(wire.out_node, wire.in_node)
    comments = inspect_comment_groups(graph)
    by_comment = {c['node_id']: c for c in comments}

    def members(comment_id, visiting=()):
        if comment_id in visiting:
            raise ValueError('cyclic Comment membership')
        result = []
        for member in by_comment[comment_id]['members']:
            result.extend(members(member, visiting + (comment_id,)) if member in by_comment else [member])
        return [i for i in result if i in ids]

    # A frame is a rigid grouping constraint, even across physical islands.
    for c in comments:
        group = members(c['node_id'])
        for i in group[1:]:
            union(group[0], i)
    islands = defaultdict(set)
    for i in sorted(ids):
        islands[find(i)].add(i)
    if not islands:
        return dict(positions), []
    labels = {}
    for key, group in islands.items():
        names = [parse_register_local_var(nodes[i])['name'] for i in group if nodes[i].type_name == REGISTER_LOCAL_VAR_TYPE]
        titles = [c['title'] for c in comments if set(members(c['node_id'])) & group]
        labels[key] = '|'.join(sorted(titles + names)) or '|'.join(sorted({nodes[i].type_name for i in group}))
    edges = {(find(a), find(b)) for a, b in local_var_edges(graph) if a in ids and b in ids and find(a) != find(b)}
    # Dependency-first, then semantic label; IDs are only the final tie breaker.
    ordered, remaining = [], set(islands)
    while remaining:
        ready = [i for i in remaining if not any(b == i and a in remaining for a, b in edges)]
        if not ready:
            raise ValueError('cyclic logical dependencies between islands')
        ready.sort(key=lambda i: (any(nodes[n].type_name in MASTER_TYPES for n in islands[i]), labels[i], sorted(islands[i])))
        chosen = ready[0]
        ordered.append(chosen)
        remaining.remove(chosen)
    outputs = [i for i in ordered if any(nodes[n].type_name in MASTER_TYPES for n in islands[i])]
    ordered = [i for i in ordered if i not in outputs] + outputs
    bounds = {}
    for i in ordered:
        rects = [node_rect(n, positions, geometry) for n in islands[i]]
        bounds[i] = (min(r[0] for r in rects) - 30, min(r[1] for r in rects) - 48,
                     max(r[2] for r in rects) + 30, max(r[3] for r in rects) + 30)
    count = min(columns, len(ordered))
    base, extra = divmod(len(ordered), count)
    buckets, start = [], 0
    for column in range(count):
        end = start + base + int(column < extra)
        buckets.append(ordered[start:end])
        start = end
    packed, report, x = dict(positions), [], 0.0
    for column, bucket in enumerate(buckets):
        y, width = 0.0, max((bounds[i][2] - bounds[i][0] for i in bucket), default=0)
        for i in bucket:
            left, top, right, bottom = bounds[i]
            dx, dy = x - left, y - top
            for n in islands[i]:
                packed[n] = (positions[n][0] + dx, positions[n][1] + dy)
            report.append({'nodes': sorted(islands[i]), 'label': labels[i], 'column': column,
                           'logical_predecessors': sorted(labels[a] for a, b in edges if b == i)})
            y += bottom - top + gap
        x += width + gap
    # Keep the main output fixed so applying the same layout twice is stable.
    anchor = next((n for i in outputs for n in sorted(islands[i]) if nodes[n].type_name in MASTER_TYPES), sorted(ids)[0])
    dx, dy = positions[anchor][0] - packed[anchor][0], positions[anchor][1] - packed[anchor][1]
    for n in ids:
        packed[n] = (round(packed[n][0] + dx, 1), round(packed[n][1] + dy, 1))
    return packed, report
