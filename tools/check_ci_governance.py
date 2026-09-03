#!/usr/bin/env python3
"""Dependency-free CI subset of the local Project Architect strict gate."""

from __future__ import annotations

import json
import re
from datetime import date
from pathlib import Path

NODE24_ACTION_REFS = {
    "actions/checkout": "93cb6efe18208431cddfb8368fd83d5badbf9bfd",
    "astral-sh/setup-uv": "20cfd1bf945f4377ade1205e4dbc17946fc9a30d",
    "actions/upload-artifact": "b7c566a772e6b6bfb58ed0dc250532a479d7789f",
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


def _action_runtime_findings(workflow_text: str) -> list[str]:
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
    for action in NODE24_ACTION_REFS:
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


def _packed_executor_loc_findings(root: Path, source_limit: int, exemptions: dict[str, dict]) -> list[str]:
    findings: list[str] = []
    seen: set[str] = set()
    for path in (root / "src/asecli").rglob("*.cs.txt"):
        relative = path.relative_to(root).as_posix()
        seen.add(relative)
        loc = len(path.read_text(encoding="utf-8").splitlines())
        exemption = exemptions.get(relative)
        if loc > source_limit and exemption is None:
            findings.append(
                f"{relative} has {loc} lines (source limit {source_limit}) and is not listed in loc_exemptions"
            )
        elif exemption is not None:
            findings.extend(_loc_exemption_governance_findings(relative, exemption))
    for relative, exemption in exemptions.items():
        target = root / relative
        if not target.is_file():
            findings.append(f"loc exemption missing file: {relative}")
        elif relative not in seen:
            findings.extend(_loc_exemption_governance_findings(relative, exemption))
    return findings


def _loc_exemption_governance_findings(
    relative: str, exemption: dict, *, today: date | None = None
) -> list[str]:
    findings: list[str] = []
    required_text = (
        "id", "path", "rule", "reason", "risk", "owner", "approved_by",
        "created_at", "expires_at", "exit_condition",
    )
    for field in required_text:
        if not isinstance(exemption.get(field), str) or not exemption[field].strip():
            findings.append(f"{relative} loc exemption is missing {field}")
    controls = exemption.get("compensating_controls")
    if not isinstance(controls, list) or not controls or any(
        not isinstance(item, str) or not item.strip() for item in controls
    ):
        findings.append(f"{relative} loc exemption has invalid compensating_controls")
    try:
        created = date.fromisoformat(str(exemption.get("created_at", "")))
        expires = date.fromisoformat(str(exemption.get("expires_at", "")))
    except ValueError:
        findings.append(f"{relative} loc exemption has invalid governance dates")
        return findings
    if expires < created or (expires - created).days > 30:
        findings.append(f"{relative} loc exemption exceeds the 30-day maximum")
    if expires < (today or date.today()):
        findings.append(f"{relative} loc exemption expired on {expires.isoformat()}")
    return findings


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    config = json.loads((root / ".project-architect.json").read_text(encoding="utf-8"))
    source_limit = config["thresholds"]["source"]["limit"]
    findings = []
    exemptions = _loc_exemptions(config)

    required = [
        "docs/00-governance/traceability.csv",
        "docs/01-architecture/module-map.md",
        "docs/03-quality/regression-catalog.md",
        "docs/04-delivery/project-plan-task-charter.md",
    ]
    findings.extend(f"missing {path}" for path in required if not (root / path).is_file())

    findings.extend(_python_loc_findings(root, config))
    findings.extend(_packed_executor_loc_findings(root, source_limit, exemptions))
    findings.extend(_audit_supplement_findings(root, config))

    private_core_import = re.compile(r"from\s+\.\.core\s+import\s+[^\n]*\b_\w+")
    for path in (root / "src/asecli").rglob("*.py"):
        if private_core_import.search(path.read_text(encoding="utf-8")):
            findings.append(f"private core import: {path.relative_to(root)}")

    hardcoded_artifact_version = re.compile(r"asecli-\d+\.\d+\.\d+")
    for path in (root / ".github/workflows").glob("*.yml"):
        workflow = path.read_text(encoding="utf-8")
        findings.extend(_action_runtime_findings(workflow))
        if hardcoded_artifact_version.search(workflow):
            findings.append(f"hard-coded asecli artifact version: {path.relative_to(root)}")
        if "shasum -a 256 dist/*.whl dist/*.tar.gz" in workflow:
            findings.append(f"non-portable artifact checksum paths: {path.relative_to(root)}")

    print(json.dumps({"ok": not findings, "findings": findings}, ensure_ascii=False))
    return 0 if not findings else 1


if __name__ == "__main__":
    raise SystemExit(main())
