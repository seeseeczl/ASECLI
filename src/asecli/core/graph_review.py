"""Conservative, port-exact baselines for post-conversion graph editing."""

from __future__ import annotations

import hashlib
from collections import defaultdict

from .commentary import COMMENTARY_TYPE
from .layout import MASTER_TYPES
from .local_vars import (
    GET_LOCAL_VAR_TYPE, REGISTER_LOCAL_VAR_TYPE,
    parse_get_local_var, parse_register_local_var,
)
from .wire_router import WIRE_NODE_TYPE


def computation_wires(graph):
    """Collapse interfaces, never discard an output component or infer a default."""
    nodes = {n.node_id: n for n in graph.nodes}
    if len(nodes) != len(graph.nodes):
        raise ValueError("duplicate node IDs")
    incoming = {}
    for w in graph.wires:
        if w.in_node not in nodes or w.out_node not in nodes:
            raise ValueError("dangling wire endpoint")
        key = (w.in_node, w.in_port)
        if key in incoming:
            raise ValueError(f"multiple connections to input {key}")
        incoming[key] = (w.out_node, w.out_port)

    def resolve(node_id, port, visiting=()):
        key = (node_id, port)
        if key in visiting:
            raise ValueError("Local Var / WireNode interface cycle")
        node = nodes[node_id]
        if node.type_name == GET_LOCAL_VAR_TYPE:
            item = parse_get_local_var(node)
            register = nodes.get(item['register_id'])
            if register is None or register.type_name != REGISTER_LOCAL_VAR_TYPE:
                raise ValueError(f"Get {node_id} has no valid Register")
            reference = parse_register_local_var(register)
            if any(item[k] != reference[k] for k in ('name', 'data_type')):
                raise ValueError(f"Get {node_id} name/type differs from Register")
            if port != '0':
                raise ValueError("unsupported Get output component; refusing to collapse")
            return resolve(register.node_id, '0', visiting + (key,))
        if node.type_name in {REGISTER_LOCAL_VAR_TYPE, WIRE_NODE_TYPE}:
            if port != '0' or (node_id, '0') not in incoming:
                raise ValueError(f"unsupported or unconnected interface {node_id}:{port}")
            return resolve(*incoming[(node_id, '0')], visiting + (key,))
        return key

    interfaces = {GET_LOCAL_VAR_TYPE, REGISTER_LOCAL_VAR_TYPE, WIRE_NODE_TYPE}
    # Validate dormant interface references too; they are not disposable nodes.
    for node in graph.nodes:
        if node.type_name in interfaces:
            resolve(node.node_id, '0')
    return sorted(
        (*resolve(w.out_node, w.out_port), w.in_node, w.in_port)
        for w in graph.wires if nodes[w.in_node].type_name not in interfaces
    )


def graph_baseline(shader):
    """Keep all non-layout fields, including opaque defaults and Master settings."""
    interfaces = {GET_LOCAL_VAR_TYPE, REGISTER_LOCAL_VAR_TYPE, WIRE_NODE_TYPE, COMMENTARY_TYPE}
    nodes = {}
    for node in shader.graph.nodes:
        if node.type_name not in interfaces:
            fields = list(node.raw_fields)
            fields[3] = '<position>'
            nodes[node.node_id] = fields
    wires = computation_wires(shader.graph)
    predecessors = defaultdict(set)
    for source, _, target, _ in wires:
        predecessors[target].add(source)
    masters = sorted(n.node_id for n in shader.graph.nodes if n.type_name in MASTER_TYPES)
    active = [n for n in masters if predecessors[n]]
    reachable, stack = set(active), list(active)
    while stack:
        for source in predecessors[stack.pop()]:
            if source not in reachable:
                reachable.add(source)
                stack.append(source)
    return {
        'schema': 'asecli.graph-baseline.v1', 'ase_version': shader.graph.version,
        'source_sha256': shader.source_digest or hashlib.sha256(shader.serialize().encode()).hexdigest(),
        'nodes': nodes, 'computation_wires': wires,
        'active_outputs': active, 'dormant_outputs': sorted(set(masters) - set(active)),
        'output_reachable': sorted(reachable),
        'retained_off_output': sorted(set(nodes) - reachable - set(masters)),
        'generated_source_sha256': hashlib.sha256(shader.prefix.encode()).hexdigest(),
        'limits': 'Raw node fields are protected; this does not prove SG defaults or rendering equivalence.',
    }


def compare_graph_baselines(before, after):
    changed = [k for k in ('ase_version', 'nodes', 'computation_wires') if before[k] != after[k]]
    return {
        'computation_equal': not changed, 'changed_sections': changed,
        'generated_source_equal': before['generated_source_sha256'] == after['generated_source_sha256'],
        'render_equivalence': 'not_verified',
        'note': 'GUI metadata changes are conservatively reported as node changes; review explicitly.',
    }
