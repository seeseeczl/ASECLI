"""Read-only Local Var policy planning keyed by source node AND output port."""

from collections import defaultdict

from .graph_review import computation_wires
from .layout_graph import immediate_comment_owners
from .local_vars import REGISTER_LOCAL_VAR_TYPE, parse_register_local_var


def plan_local_var_reuse(graph, *, policy='consumer-groups'):
    if policy not in {'consumer-groups', 'fanout'}:
        raise ValueError('unknown Local Var reuse policy')
    owners = immediate_comment_owners(graph)
    consumers = defaultdict(list)
    for source, port, target, input_port in computation_wires(graph):
        consumers[(source, port)].append((target, input_port))
    nodes = {n.node_id: n for n in graph.nodes}
    # Find existing direct registrations, never propose duplicate registrations.
    registers = defaultdict(list)
    for wire in graph.wires:
        if nodes[wire.in_node].type_name == REGISTER_LOCAL_VAR_TYPE:
            registers[(wire.out_node, wire.out_port)].append(parse_register_local_var(nodes[wire.in_node]))
    result = []
    for (source, port), targets in sorted(consumers.items()):
        groups = sorted({owners[t] for t, _ in targets if t in owners})
        selected = len(targets) >= 2 if policy == 'fanout' else len(groups) >= 2
        direct = [
            {'node': w.in_node, 'port': w.in_port}
            for w in graph.wires
            if (w.out_node, w.out_port) == (source, port)
            and nodes[w.in_node].type_name != REGISTER_LOCAL_VAR_TYPE
            and (policy == 'fanout' or owners.get(w.in_node) != owners.get(source))
        ]
        if len(registers[(source, port)]) > 1:
            raise ValueError(f'multiple Registers for {source}:{port}; resolve explicitly')
        result.append({
            'source_node': source, 'source_port': port, 'uses': len(targets),
            'consumers': [{'node': t, 'port': p} for t, p in targets],
            'consumer_groups': groups, 'policy': policy,
            'required': selected, 'existing_registers': registers[(source, port)],
            'direct_consumers_to_replace': direct if selected else [],
            'action': ('reuse_register' if registers[(source, port)] else 'create_register')
            if selected and direct else 'keep',
            'authoring': 'requires_current_ASE_API_and_semantic_name',
        })
    return result
