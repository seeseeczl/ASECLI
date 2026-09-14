"""Conservative precision proof for moving graph arithmetic into URP."""

import re

from .alpha_modulate import _strip_comments
from .model import diagnostic


def fold_precision_verified(node, nodes, edges, report, semantics):
    """Do not replace float/inherited lerp with URP's half3/half overload.

    Custom Function parameters establish their own half conversion boundary.
    Native lerp additionally needs explicitly half operands (no mixed promotion).
    This is a narrow proof, not an assertion that half equals float on every GPU.
    """
    precision = node.settings.get("precision", "Inherit")
    effective_precision = precision
    verified = precision == "Half"
    body = None
    if node.target_type == "custom-function":
        body = _strip_comments((node.function or {}).get("body", ""))
        if body and re.search(r"\bfloat(?:[1-4])?\s*\(", body):
            effective_precision = "Single"
        elif body and re.search(r"\bhalf(?:[1-4])?\s*\(", body):
            effective_precision = "Half"
        verified = verified and body is not None and bool(re.search(r"\bhalf3\s*\(", body))
    else:
        by_id = {item.target_id: item for item in nodes}
        operands = [by_id.get(edge.source_id) for edge in edges if edge.target_id == node.target_id]
        verified = verified and bool(operands) and all(
            item is not None and item.settings.get("precision") == "Half" for item in operands
        )
    proof = {
        "source_node_id": node.source_id,
        "source_node_precision": precision,
        "source_effective_precision": effective_precision,
        "source_expression": body,
        "target_precision": "Half",
        "target_function": "half3 AlphaModulate(half3 albedo, half alpha)",
        "status": "verified" if verified else "unproven",
    }
    semantics["fold_precision"] = proof
    if not verified:
        requirement = {
            "surface": semantics.get("source", {}).get("surface"),
            "rgb_blend": (semantics.get("source_pass_blend") or {}).get("rgb"),
            "alpha_blend": (semantics.get("source_pass_blend") or {}).get("alpha"),
            "explicit_alpha_modulate": {
                "preserve_in_graph": True,
                "precision": effective_precision,
                "source_node_id": node.source_id,
            },
            "implicit_alpha_modulate": False,
        }
        semantics["required_target_capabilities"] = requirement
        semantics["unresolved"] = {
            "rule": "SEM-BLEND-001",
            "source_node": node.source_id,
            "reason": "target cannot preserve explicit AlphaModulate precision while disabling its implicit AlphaModulate",
        }
        report.setdefault("diagnostics", []).append(diagnostic(
            node.source_id, "ALPHA_MODULATE_TARGET_CAPABILITY_REQUIRED",
            {"precision_proof": proof, "required_target_capabilities": requirement},
            "The current public SG target contract cannot preserve this graph expression and blend equation without adding a second half-precision AlphaModulate",
        ))
    return verified
