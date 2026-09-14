"""Record precision boundaries separately from certified algorithm rewrites."""

import re

from .alpha_modulate import _strip_comments


def record_fold_precision(node, nodes, edges, report, semantics):
    """Called only after expression, inputs and blend equations match.

    A precision boundary is not a proof of bitwise or visual equivalence.
    Explicit body types are evidence, not the effective type of a whole function.
    """
    declared = node.settings.get("precision", "Inherit")
    graph = report.get("source_graph_precision")
    inherited = declared in {"Inherit", "Graph"}
    resolved = graph if inherited else declared
    body = (_strip_comments((node.function or {}).get("body", ""))
            if node.target_type == "custom-function" else None)
    explicit = sorted(set(re.findall(r"\b(?:float|half)(?:[1-4])?\b", body or "")))
    by_id = {item.target_id: item for item in nodes}
    operands = [by_id.get(edge.source_id) for edge in edges if edge.target_id == node.target_id]
    operand_precisions = [item.settings.get("precision", "Inherit") if item else "Unknown"
                          for item in operands]
    half_boundary = resolved == "Half" and (
        (bool(explicit) and all(t.startswith("half") for t in explicit))
        if body is not None else
        (bool(operands) and all((graph if p in {"Inherit", "Graph"} else p) == "Half"
                               for p in operand_precisions))
    )
    proof = {
        "source_node_id": node.source_id,
        "source_node_precision": declared,
        "source_graph_precision": graph,
        "inheritance_source": "graph" if inherited else "node",
        "source_resolved_precision": resolved or "Unknown",
        "source_explicit_types": explicit,
        "source_operand_precisions": operand_precisions,
        "source_expression": body,
        "target_precision": "Half",
        "target_function": "half3 AlphaModulate(half3 albedo, half alpha)",
        "status": "matched_half_boundary" if half_boundary else "precision_difference_or_unknown",
        "bitwise_equivalence": "not_proven",
        "transformation": "fold_explicit_alpha_modulate_into_pipeline",
    }
    semantics["fold_precision"] = proof
    if not half_boundary:
        report.setdefault("precision_warnings", []).append({
            "code": "ALPHA_MODULATE_PRECISION_BOUNDARY",
            "source_node_id": node.source_id,
            "classification": "precision",
            "evidence": proof,
            "impact": "Certified mathematical mapping preserves one modulation and blend factors; "
                      "the pipeline half boundary may change rounding or representable range. "
                      "Bitwise and visual equivalence have not been verified.",
        })
