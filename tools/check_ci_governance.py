#!/usr/bin/env python3
"""Dependency-free CI subset of the local Project Architect strict gate."""

from __future__ import annotations

import json
import re
from pathlib import Path

try:
    from .check_document_governance import document_governance_findings
except ImportError:  # Direct script execution from the tools directory.
    from check_document_governance import document_governance_findings

try:
    from .check_packed_executor_loc import (
        _loc_exemption_governance_findings,
        _packed_executor_loc_findings,
    )
except ImportError:
    from check_packed_executor_loc import (
        _loc_exemption_governance_findings,
        _packed_executor_loc_findings,
    )

NODE24_ACTION_REFS = {
    "actions/checkout": "93cb6efe18208431cddfb8368fd83d5badbf9bfd",
    "astral-sh/setup-uv": "20cfd1bf945f4377ade1205e4dbc17946fc9a30d",
    "actions/upload-artifact": "b7c566a772e6b6bfb58ed0dc250532a479d7789f",
    "actions/download-artifact": "3e5f45b2cfb9172054b4087a40e8e0b5a5461e7c",
}
REQUIRED_CI_ACTIONS = {
    "actions/checkout",
    "astral-sh/setup-uv",
    "actions/upload-artifact",
}


def _loc_exemptions(config: dict) -> dict[str, dict]:
    items = config.get("loc_exemptions")
    if not isinstance(items, list):
        return {}
    result: dict[str, dict] = {}
    for item in items:
        if isinstance(item, dict) and isinstance(item.get("path"), str):
            result[item["path"]] = item
    return result


def _action_runtime_findings(
    workflow_text: str, *, required_actions: set[str] | None = None
) -> list[str]:
    findings: list[str] = []
    action_refs = re.findall(r"^\s*-?\s*uses:\s*([^\s@]+)@([0-9a-f]{40})", workflow_text, re.MULTILINE)
    seen: set[str] = set()
    for action, sha in action_refs:
        expected = NODE24_ACTION_REFS.get(action)
        if expected is None:
            continue
        seen.add(action)
        if sha != expected:
            findings.append(
                f"{action} must use the approved Node 24 commit {expected}, got {sha}"
            )
    for action in required_actions or ():
        if action not in seen:
            findings.append(f"approved Node 24 action is missing: {action}")
    return findings


def _audit_supplement_findings(root: Path, config: dict) -> list[str]:
    findings: list[str] = []
    relative = config.get("audit", {}).get("supplement")
    if not isinstance(relative, str) or not relative.strip():
        return ["audit.supplement is missing"]
    path = root / relative
    if not path.is_file():
        return [f"audit supplement missing file: {relative}"]
    payload = json.loads(path.read_text(encoding="utf-8"))
    modules = payload.get("functional_modules") if isinstance(payload, dict) else None
    if not isinstance(modules, list) or len(modules) != 14:
        return ["audit supplement must contain exactly 14 functional_modules"]
    ids: list[str] = []
    for module in modules:
        if not isinstance(module, dict):
            findings.append("audit supplement functional module must be an object")
            continue
        module_id = module.get("id")
        if not isinstance(module_id, str) or not re.fullmatch(r"FM-[0-9A-F]{10}", module_id):
            findings.append(f"invalid functional module id: {module_id!r}")
        else:
            ids.append(module_id)
        evidence_paths = module.get("evidence_paths")
        if not isinstance(evidence_paths, list) or not evidence_paths:
            findings.append(f"{module_id} has no evidence_paths")
            continue
        for evidence in evidence_paths:
            if not isinstance(evidence, str) or not (root / evidence).exists():
                findings.append(f"{module_id} evidence path is missing: {evidence!r}")
    if len(ids) != len(set(ids)):
        findings.append("audit supplement functional module ids are not unique")
    return findings


def _python_loc_findings(root: Path, config: dict) -> list[str]:
    findings: list[str] = []
    thresholds = config["thresholds"]
    for root_name in config["source_roots"]:
        source_root = root / root_name
        if not source_root.is_dir():
            findings.append(f"LOC source root is missing: {root_name}")
            continue
        category = "test" if root_name == "tests" else "source"
        warning = thresholds[category]["warning"]
        for path in source_root.rglob("*.py"):
            loc = len(path.read_text(encoding="utf-8").splitlines())
            if loc > warning:
                findings.append(
                    f"{path.relative_to(root)} has {loc} lines ({category} strict warning limit {warning})"
                )
    return findings


def _release_record_findings(root: Path) -> list[str]:
    findings = []
    release_root = root / "docs/04-delivery/releases"
    for path in release_root.glob("REL-*.md"):
        text = path.read_text(encoding="utf-8")
        if not re.search(r"^status:\s*released\s*$", text, re.MULTILINE):
            continue
        if re.search(r"\bpending\b|待回填", text, re.IGNORECASE):
            findings.append(
                f"released record contains pending evidence: {path.relative_to(root)}"
            )
    return findings


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    config = json.loads((root / ".project-architect.json").read_text(encoding="utf-8"))
    source_limit = config["thresholds"]["source"]["limit"]
    source_warning = config["thresholds"]["source"]["warning"]
    findings = []
    exemptions = _loc_exemptions(config)
    warning_baselines = config.get("packed_executor_warning_baselines", {})
    if not isinstance(warning_baselines, dict):
        warning_baselines = {}

    required = [
        "docs/00-governance/traceability.csv",
        "docs/01-architecture/module-map.md",
        "docs/03-quality/regression-catalog.md",
        "docs/04-delivery/project-plan-task-charter.md",
    ]
    findings.extend(f"missing {path}" for path in required if not (root / path).is_file())

    findings.extend(_python_loc_findings(root, config))
    findings.extend(
        _packed_executor_loc_findings(
            root, source_warning, source_limit, exemptions, warning_baselines
        )
    )
    findings.extend(_audit_supplement_findings(root, config))
    findings.extend(_release_record_findings(root))
    findings.extend(document_governance_findings(root))

    private_core_import = re.compile(r"from\s+\.\.core\s+import\s+[^\n]*\b_\w+")
    for path in (root / "src/asecli").rglob("*.py"):
        if private_core_import.search(path.read_text(encoding="utf-8")):
            findings.append(f"private core import: {path.relative_to(root)}")

    hardcoded_artifact_version = re.compile(r"asecli-\d+\.\d+\.\d+")
    for path in (root / ".github/workflows").glob("*.yml"):
        workflow = path.read_text(encoding="utf-8")
        required = REQUIRED_CI_ACTIONS if path.name == "ci.yml" else None
        findings.extend(_action_runtime_findings(workflow, required_actions=required))
        if hardcoded_artifact_version.search(workflow):
            findings.append(f"hard-coded asecli artifact version: {path.relative_to(root)}")
        if "shasum -a 256 dist/*.whl dist/*.tar.gz" in workflow:
            findings.append(f"non-portable artifact checksum paths: {path.relative_to(root)}")

    publish = (root / ".github/workflows/publish.yml").read_text(encoding="utf-8")
    release_markers = (
        "tools/check_release_candidate.py", "pytest -q",
        "tools/check_regression_catalog.py", "tools/check_ci_governance.py",
        "tools/compare_build_artifacts.py", "tools/generate_sbom.py",
        "tools/supply_chain_check.py", "shasum -a 256 -c SHA256SUMS",
        "vars.ASECLI_PYPI_ENABLED == 'true'",
        "uv publish dist/*.whl dist/*.tar.gz",
    )
    for marker in release_markers:
        if marker not in publish:
            findings.append(f"publish workflow missing release gate: {marker}")

    print(json.dumps({"ok": not findings, "findings": findings}, ensure_ascii=False))
    return 0 if not findings else 1


if __name__ == "__main__":
    raise SystemExit(main())
