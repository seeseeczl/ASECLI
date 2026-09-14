"""Expose bounded surface-semantic evidence in the public conversion report."""

from __future__ import annotations

from typing import Any


_VERIFIED_EVIDENCE = {
    "properties": "ASE properties reconciled with ShaderLab declarations",
    "resources": "all texture dependencies are null or have matching importer evidence",
    "graph_algorithm": "certified ASE nodes, defaults and wires were deterministically mapped",
    "target": "certified URP Unlit Master settings were mapped",
    "passes": "the certified ASE URP Unlit pass set was recognized",
    "alpha_equation": "opaque alpha behavior or the explicit Alpha block binding was preserved",
    "blend_equation": "the certified ASE Master blend mode was mapped to the SG target",
}
_SEMANTIC_CODES = {
    "ALPHA_BLEND_UNREPRESENTABLE", "PASS_BLEND_UNPROVEN",
    "DUPLICATE_ALPHA_MODULATE_UNRESOLVED", "ALPHA_MODULATE_UNPROVEN",
}


def check_evidence(
    name: str, state: str, internal: dict[str, Any] | None, failure: str | None
) -> str:
    details = _blend_details(name, internal)
    if state == "verified":
        return _VERIFIED_EVIDENCE[name] + details
    diagnostics = internal.get("diagnostics", []) if isinstance(internal, dict) else []
    codes = _SEMANTIC_CODES if name in {"alpha_equation", "blend_equation"} else set()
    relevant = next((item for item in diagnostics if item.get("code") in codes), None)
    if relevant:
        return f"{relevant['code']}: {relevant.get('reason', 'not proven')}" + details
    if failure:
        return f"conversion stopped before this invariant was proved: {failure}" + details
    if diagnostics:
        first = diagnostics[0]
        return f"{first.get('code', 'UNPROVEN')}: {first.get('reason', 'not proven')}"
    if name in {"alpha_equation", "blend_equation"}:
        return "the source target equation could not be proved from the certified Master mapping" + details
    return "not proven by the producer-only export"


def _blend_details(name: str, internal: dict[str, Any] | None) -> str:
    if name not in {"alpha_equation", "blend_equation"} or not isinstance(internal, dict):
        return ""
    semantics = internal.get("surface_semantics", {}) if isinstance(internal, dict) else {}
    parser = semantics.get("pass_blend_parser") or {}
    rewrites = semantics.get("rewrites") or []
    matcher = (
        "unresolved" if semantics.get("unresolved")
        else "folded" if rewrites
        else "preserved_graph_float_expression"
        if semantics.get("alpha_modulate_strategy") == "preserve_graph_float_expression"
        else "not_detected"
    )
    return (
        f"; pass_parser={parser.get('status', 'missing')}"
        f" candidates={parser.get('candidate_count', 0)}"
        f" source={semantics.get('source_pass_blend')}"
        f" target={semantics.get('target_pass_blend')}"
        f" alpha_modulate=matcher-v4/{matcher}"
    )
