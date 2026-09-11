"""Build the shared fail-closed conversion report for ASECLI exports."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


CHECK_RULES = {
    "properties": "SEM-PROP-001",
    "resources": "SEM-RESOURCE-001",
    "graph_algorithm": "SEM-GRAPH-001",
    "target": "SEM-TARGET-001",
    "passes": "SEM-PASS-001",
    "alpha_equation": "SEM-ALPHA-001",
    "blend_equation": "SEM-BLEND-001",
}


def assert_spec_publishable(report: dict[str, Any]) -> None:
    unknown = [
        name for name in CHECK_RULES
        if report.get("checks", {}).get(name, {}).get("status") != "verified"
    ]
    evidence = report.get("evidence", {})
    if unknown or evidence.get("source_parsed") != "passed" or evidence.get(
        "semantic_mapped"
    ) != "passed" or evidence.get("producer_schema_validated") != "passed":
        raise ValueError(
            "formal specification is not publishable; unverified semantics: "
            + (", ".join(unknown) if unknown else "producer evidence")
        )


def build_public_report(
    source: Path,
    spec_path: Path,
    spec: dict[str, Any] | None,
    internal: dict[str, Any] | None,
    *,
    failure: str | None = None,
    source_raw: bytes | None = None,
    source_recheck_raw: bytes | None = None,
    producer_schema_validated: str = "not_run",
    source_format: str = "ase",
) -> dict[str, Any]:
    if source_raw is None:
        source_raw = source.read_bytes() if source.is_file() else b""
    if source_recheck_raw is None:
        source_recheck_raw = source.read_bytes() if source.is_file() else b""
    spec_raw = (
        (json.dumps(spec, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
        if spec is not None
        else b""
    )
    semantic_passed = _verification(internal, "semantic_mapping") == "passed"
    source_passed = _verification(internal, "source_parse") == "passed"
    resources_passed = semantic_passed and _resources_verified(internal)
    passes_passed = semantic_passed and _pass_mapping_present(internal)
    alpha_passed = semantic_passed and _alpha_equation_verified(internal)
    blend_passed = semantic_passed and _blend_equation_verified(internal)
    check_status = {
        "properties": "verified" if semantic_passed else "unsupported",
        "resources": "verified" if resources_passed else "unknown",
        "graph_algorithm": "verified" if semantic_passed else "unsupported",
        "target": "verified" if semantic_passed else "unsupported",
        "passes": "verified" if passes_passed else "unknown",
        "alpha_equation": "verified" if alpha_passed else "unknown",
        "blend_equation": "verified" if blend_passed else "unknown",
    }
    checks = {
        name: {
            "rule": rule,
            "status": check_status[name],
            "evidence": _check_evidence(name, check_status[name], internal, failure),
        }
        for name, rule in CHECK_RULES.items()
    }
    degradations = [
        {
            "rule": CHECK_RULES[name],
            "category": "unsupported" if check["status"] == "unsupported" else "evidence_gap",
            "source": str(source),
            "target": str(spec_path),
            "reason": check["evidence"],
        }
        for name, check in checks.items()
        if check["status"] != "verified"
    ]
    degradations.extend([
        {
            "rule": "SEM-EVIDENCE-001",
            "category": "evidence_gap",
            "source": str(source),
            "target": str(spec_path),
            "reason": "SGCLI schema acceptance, Editor create, save/reload, compile, canvas and render evidence have not run",
        },
        {
            "rule": "SEM-COMPARE-001",
            "category": "evidence_gap",
            "source": str(source),
            "target": str(spec_path),
            "reason": "same-condition rendering inputs have not been matched",
        },
    ])
    if failure:
        degradations.append({
            "rule": "SEM-REPORT-001",
            "category": "unsupported",
            "source": str(source),
            "target": str(spec_path),
            "reason": f"specification was not generated: {failure}",
        })
    return {
        "schema": "sgcli.shader-conversion-report.v1",
        "source": {
            "path": str(source),
            "sha256": hashlib.sha256(source_raw).hexdigest(),
            "format": source_format,
            "source_snapshot_sha256": hashlib.sha256(source_raw).hexdigest(),
            "source_recheck_sha256": hashlib.sha256(source_recheck_raw).hexdigest(),
        },
        "target": {
            "path": str(spec_path),
            "sha256": hashlib.sha256(spec_raw).hexdigest(),
            "format": "sgcli-native-spec",
        },
        "conversion_success": False,
        "visual_equivalent": False,
        "checks": checks,
        "evidence": {
            "source_parsed": "passed" if source_passed else "failed",
            "semantic_mapped": "passed" if semantic_passed else "failed",
            "producer_schema_validated": producer_schema_validated,
            "consumer_loaded": "not_run",
            "editor_created": "not_run",
            "save_reload": "not_run",
            "compiled": "not_run",
            "canvas_reviewed": "not_run",
            "render_compared": "not_run",
        },
        "comparison_conditions": {
            name: "not_run"
            for name in (
                "material_values",
                "camera",
                "time",
                "resolution",
                "render_pipeline",
                "render_target_and_post",
                "color_space",
            )
        },
        "degradations": degradations,
    }


def _verification(internal: dict[str, Any] | None, name: str) -> str:
    if not isinstance(internal, dict):
        return "not_run"
    value = internal.get("verification", {}).get(name, {})
    return value.get("status", "not_run") if isinstance(value, dict) else "not_run"


def _resources_verified(internal: dict[str, Any] | None) -> bool:
    if not isinstance(internal, dict):
        return False
    return all(
        isinstance(item, dict) and item.get("status") in {"verified_importer", "explicit_null"}
        for item in internal.get("dependencies", [])
    )


def _pass_mapping_present(internal: dict[str, Any] | None) -> bool:
    if not isinstance(internal, dict):
        return False
    return any(
        isinstance(item, dict) and item.get("kind") == "certified_template_pass_set"
        for item in internal.get("mappings", [])
    )


def _alpha_equation_verified(internal: dict[str, Any] | None) -> bool:
    if not isinstance(internal, dict):
        return False
    target = internal.get("target_mapping", {})
    if target.get("surface") == "Opaque":
        return True
    return any(
        isinstance(item, dict)
        and item.get("block") == "SurfaceDescription.Alpha"
        for item in internal.get("output_bindings", [])
    )


def _blend_equation_verified(internal: dict[str, Any] | None) -> bool:
    if not isinstance(internal, dict):
        return False
    target = internal.get("target_mapping", {})
    return target.get("blend") in {"Alpha", "Premultiply", "Additive", "Multiply"}


def _check_evidence(
    name: str,
    state: str,
    internal: dict[str, Any] | None,
    failure: str | None,
) -> str:
    if state == "verified":
        return {
            "properties": "ASE properties reconciled with ShaderLab declarations",
            "resources": "all texture dependencies are null or have matching importer evidence",
            "graph_algorithm": "certified ASE nodes, defaults and wires were deterministically mapped",
            "target": "certified URP Unlit Master settings were mapped",
            "passes": "the certified ASE URP Unlit pass set was recognized",
            "alpha_equation": "opaque alpha behavior or the explicit Alpha block binding was preserved",
            "blend_equation": "the certified ASE Master blend mode was mapped to the SG target",
        }[name]
    if failure:
        return f"conversion stopped before this invariant was proved: {failure}"
    diagnostics = internal.get("diagnostics", []) if isinstance(internal, dict) else []
    if diagnostics:
        first = diagnostics[0]
        return f"{first.get('code', 'UNPROVEN')}: {first.get('reason', 'not proven')}"
    if name in {"alpha_equation", "blend_equation"}:
        return "the source target equation could not be proved from the certified Master mapping"
    return "not proven by the producer-only export"
