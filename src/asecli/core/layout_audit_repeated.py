"""Repeated-subtree consistency diagnostics for meticulous layout."""

TEMPLATE_TOLERANCE = 8.0


def repeated_module_mismatches(graph, plan) -> list[dict]:
    types = {node.node_id: node.type_name for node in graph.nodes}
    signatures: dict[tuple, list[str]] = {}
    for parent, children in plan.children.items():
        if children:
            signature = _tree_signature(parent, plan, types)
            signatures.setdefault(signature, []).append(parent)
    issues = []
    for parents in signatures.values():
        if len(parents) < 2:
            continue
        baseline = _relative_profile(parents[0], plan)
        for parent in parents[1:]:
            profile = _relative_profile(parent, plan)
            if len(profile) != len(baseline) or any(
                abs(a - b) > TEMPLATE_TOLERANCE for a, b in zip(profile, baseline)
            ):
                issues.append({"baseline": parents[0], "node_id": parent})
    return issues


def _relative_profile(parent, plan) -> tuple[float, ...]:
    origin_x, origin_y = plan.positions[parent]
    values = []
    stack = [parent]
    while stack:
        node_id = stack.pop()
        if node_id != parent:
            x, y = plan.positions[node_id]
            values.extend((round(x - origin_x, 3), round(y - origin_y, 3)))
        stack.extend(reversed(plan.children[node_id]))
    return tuple(values)


def _tree_signature(node_id, plan, types):
    return (
        types[node_id],
        tuple(_tree_signature(child, plan, types) for child in plan.children[node_id]),
    )
