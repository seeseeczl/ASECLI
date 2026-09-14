"""Target-aware surface output normalization for ASE -> Shader Graph.

ASE templates may represent pipeline behavior as explicit graph nodes.  Shader
Graph targets can perform the same work implicitly, so copying both the graph
node and the target setting changes the final pixel equation.  This module is
the boundary where graph and target semantics are combined before a native SG
candidate is published.
"""

from __future__ import annotations

from .alpha_modulate import inputs as alpha_modulate_inputs
from .model import SemanticEdge, SemanticNode, diagnostic
from .pass_blend import record_pass_blend
from .surface_precision import record_fold_precision
from .surface_matching import (
    _input_port,
    _native_alpha_modulate,
    _single_edge_to,
    _target_alpha_modulates,
    _through_reroutes,
    _unproven_modulation,
    _unresolved_modulation,
)


BASE_COLOR = "SurfaceDescription.BaseColor"
SURFACE_ALPHA = "SurfaceDescription.Alpha"


def normalize_surface_outputs(
    nodes: list[SemanticNode],
    edges: list[SemanticEdge],
    target: dict,
    mappings: dict,
    report: dict,
    source_text: str | None = None,
) -> tuple[list[SemanticNode], list[SemanticEdge]]:
    """Fold explicit ASE compensation already supplied by the SG target.

    The rewrite is intentionally narrow.  It is only valid when the explicit
    lerp alpha input is exactly the same endpoint as Surface Alpha and the
    target is URP Transparent/Multiply, whose pass performs AlphaModulate.
    """
    source_target_blend = target.get("blend")
    _select_exact_multiply_target(target, source_text)
    semantics = {
        "source": {
            "surface": target.get("surface"),
            "blend": source_target_blend,
        },
        "target_pipeline": {
            "implicit_alpha_modulate": _target_alpha_modulates(target),
        },
        "alpha_modulate_strategy": (
            "preserve_graph_float_expression"
            if target.get("blend") == "MultiplySourceAlpha"
            else "pipeline_fold"
        ),
        "rewrites": [],
    }
    report["surface_semantics"] = semantics
    record_pass_blend(semantics, target, source_text)
    if semantics.get("alpha_blend_equivalent") is False:
        report.setdefault("diagnostics", []).append(diagnostic(
            None,
            "ALPHA_BLEND_UNREPRESENTABLE",
            {
                "source": semantics.get("source_pass_blend"),
                "target": semantics.get("target_pass_blend"),
            },
            "The standard URP Shader Graph target cannot preserve the source alpha-channel blend factors",
        ))
    elif target.get("surface") == "Transparent" and (
        semantics.get("rgb_blend_equivalent") is not True
        or semantics.get("alpha_blend_equivalent") is not True
    ):
        report.setdefault("diagnostics", []).append(diagnostic(
            None,
            "PASS_BLEND_UNPROVEN",
            semantics.get("pass_blend_parser", {}),
            "The source Forward-pass RGB and alpha blend factors were not uniquely proved",
        ))
    if (target.get("surface") == "Transparent" and (
        semantics.get("rgb_blend_equivalent") is not True
        or semantics.get("alpha_blend_equivalent") is not True
    )):
        return nodes, edges
    if not semantics["target_pipeline"]["implicit_alpha_modulate"]:
        return nodes, edges

    by_id = {node.target_id: node for node in nodes}
    color_edge = _single_edge_to(edges, BASE_COLOR)
    alpha_edge = _single_edge_to(edges, SURFACE_ALPHA)
    if color_edge is None or alpha_edge is None:
        return nodes, edges
    node = by_id.get(color_edge.source_id)
    if node is None:
        return nodes, edges
    native = _native_alpha_modulate(nodes, edges, color_edge, alpha_edge)
    if native is not None:
        modulate, color_input, alpha_input, route_nodes, white_node = native
        record_fold_precision(modulate, nodes, edges, report, semantics)
        replacement = SemanticEdge(
            color_input.source_id,
            color_input.source_port,
            color_edge.target_id,
            color_edge.target_port,
        )
        rewritten = [replacement if edge == color_edge else edge for edge in edges]
        removable_ids = {modulate.target_id, *(item.target_id for item in route_nodes)}
        external_consumers = [
            edge for edge in rewritten
            if edge.source_id in removable_ids and edge.target_id not in removable_ids
        ]
        removed = not external_consumers
        if removed:
            rewritten = [
                edge for edge in rewritten
                if edge.source_id not in removable_ids and edge.target_id not in removable_ids
            ]
            nodes = [item for item in nodes if item.target_id not in removable_ids]
            for item in [modulate, *route_nodes]:
                mappings.pop(item.source_id, None)
            if white_node is not None and not any(
                edge.source_id == white_node.target_id for edge in rewritten
            ):
                rewritten = [
                    edge for edge in rewritten if edge.target_id != white_node.target_id
                ]
                nodes = [item for item in nodes if item.target_id != white_node.target_id]
                mappings.pop(white_node.source_id, None)
        semantics["source"].update({
            "explicit_alpha_modulate": True,
            "base_color_input": [color_input.source_id, color_input.source_port],
            "alpha_input": [alpha_input.source_id, alpha_input.source_port],
        })
        semantics["rewrites"].append({
            "rule": "SEM-BLEND-001",
            "kind": "fold_native_lerp_alpha_modulate_into_multiply_target",
            "source_node": modulate.source_id,
            "target_node": modulate.target_id,
            "removed": removed,
            "base_color_before": [color_edge.source_id, color_edge.source_port],
            "base_color_after": [replacement.source_id, replacement.source_port],
            "alpha_endpoint": [alpha_edge.source_id, alpha_edge.source_port],
            "source_modulation_count": 1,
            "target_modulation_count": 1,
            "matcher_version": 4,
        })
        for row in report.get("mappings", []):
            if modulate.source_id in row.get("source_nodes", []):
                row["kind"] = "pipeline_compensation_folded"
                row["target_nodes"] = [] if removed else row.get("target_nodes", [])
                row["rule"] = "SEM-BLEND-001"
        return nodes, rewritten
    source_edge, route_nodes = _through_reroutes(color_edge, by_id, edges)
    node = by_id.get(source_edge.source_id)
    if node is None:
        return nodes, edges
    matched = (
        alpha_modulate_inputs(node.function)
        if node.target_type == "custom-function"
        else None
    )
    if matched is None:
        if node.target_type == "custom-function":
            _unproven_modulation(report, semantics, node)
        return nodes, edges
    color_input_name, alpha_input_name = matched
    color_port = _input_port(node, color_input_name)
    alpha_port = _input_port(node, alpha_input_name)
    if color_port is None or alpha_port is None:
        return nodes, edges
    color_input = _single_edge_to(edges, node.target_id, -1 - color_port)
    alpha_input = _single_edge_to(edges, node.target_id, -1 - alpha_port)
    if color_input is None or alpha_input is None:
        _unresolved_modulation(report, semantics, node, "AlphaModulate inputs are not uniquely connected")
        return nodes, edges
    if (alpha_input.source_id, alpha_input.source_port) != (
        alpha_edge.source_id,
        alpha_edge.source_port,
    ):
        _unresolved_modulation(
            report,
            semantics,
            node,
            "AlphaModulate alpha input differs from Surface Alpha",
        )
        return nodes, edges
    record_fold_precision(node, nodes, edges, report, semantics)
    replacement = SemanticEdge(
        color_input.source_id,
        color_input.source_port,
        color_edge.target_id,
        color_edge.target_port,
    )
    rewritten = [replacement if edge == color_edge else edge for edge in edges]
    removable_ids = {node.target_id, *(item.target_id for item in route_nodes)}
    external_consumers = [edge for edge in rewritten
                          if edge.source_id in removable_ids and edge.target_id not in removable_ids]
    removed = not external_consumers
    if removed:
        rewritten = [edge for edge in rewritten
                     if edge.source_id not in removable_ids and edge.target_id not in removable_ids]
        nodes = [item for item in nodes if item.target_id not in removable_ids]
        for item in [node, *route_nodes]:
            mappings.pop(item.source_id, None)

    semantics["source"].update({
        "explicit_alpha_modulate": True,
        "base_color_input": [color_input.source_id, color_input.source_port],
        "alpha_input": [alpha_input.source_id, alpha_input.source_port],
    })
    semantics["rewrites"].append({
        "rule": "SEM-BLEND-001",
        "kind": "fold_explicit_alpha_modulate_into_multiply_target",
        "source_node": node.source_id,
        "target_node": node.target_id,
        "removed": removed,
        "base_color_before": [color_edge.source_id, color_edge.source_port],
        "base_color_after": [replacement.source_id, replacement.source_port],
        "alpha_endpoint": [alpha_edge.source_id, alpha_edge.source_port],
        "source_modulation_count": 1,
        "target_modulation_count": 1,
        "matcher_version": 4,
    })
    for row in report.get("mappings", []):
        if node.source_id in row.get("source_nodes", []):
            row["kind"] = "pipeline_compensation_folded"
            row["target_nodes"] = [] if removed else row.get("target_nodes", [])
            row["rule"] = "SEM-BLEND-001"
    return nodes, rewritten


def _select_exact_multiply_target(target: dict, source_text: str | None) -> None:
    """Select the project-supported Multiply variant that writes source alpha."""
    if target.get("surface") != "Transparent" or target.get("blend") != "Multiply":
        return
    from .pass_blend import forward_blend

    source = forward_blend(source_text or "")
    if source == {
        "rgb": ["DstColor", "Zero"],
        "alpha": ["One", "Zero"],
    }:
        target["blend"] = "MultiplySourceAlpha"
