#!/usr/bin/env python3
"""Dependency-free CI subset of the local Project Architect strict gate."""

from __future__ import annotations

import json
import re
from pathlib import Path


def _loc_exemptions(config: dict) -> dict[str, dict]:
    items = config.get("loc_exemptions")
    if not isinstance(items, list):
        return {}
    result: dict[str, dict] = {}
    for item in items:
        if isinstance(item, dict) and isinstance(item.get("path"), str):
            result[item["path"]] = item
    return result


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
        elif exemption is not None and not str(exemption.get("reason", "")).strip():
            findings.append(f"{relative} loc exemption is missing a reason")
    for relative, exemption in exemptions.items():
        target = root / relative
        if not target.is_file():
            findings.append(f"loc exemption missing file: {relative}")
        elif relative not in seen and not str(exemption.get("reason", "")).strip():
            findings.append(f"{relative} loc exemption is missing a reason")
    return findings


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    config = json.loads((root / ".project-architect.json").read_text(encoding="utf-8"))
    limit = config["loc_thresholds"]["source"]["warning"]
    source_limit = config["loc_thresholds"]["source"]["limit"]
    findings = []
    exemptions = _loc_exemptions(config)

    required = [
        "docs/00-governance/traceability.csv",
        "docs/01-architecture/module-map.md",
        "docs/03-quality/regression-catalog.md",
        "docs/04-delivery/project-plan-task-charter.md",
    ]
    findings.extend(f"missing {path}" for path in required if not (root / path).is_file())

    for path in (root / "src/asecli").rglob("*.py"):
        loc = len(path.read_text(encoding="utf-8").splitlines())
        if loc > limit:
            findings.append(f"{path.relative_to(root)} has {loc} lines (strict warning limit {limit})")

    findings.extend(_packed_executor_loc_findings(root, source_limit, exemptions))

    private_core_import = re.compile(r"from\s+\.\.core\s+import\s+[^\n]*\b_\w+")
    for path in (root / "src/asecli").rglob("*.py"):
        if private_core_import.search(path.read_text(encoding="utf-8")):
            findings.append(f"private core import: {path.relative_to(root)}")

    hardcoded_artifact_version = re.compile(r"asecli-\d+\.\d+\.\d+")
    for path in (root / ".github/workflows").glob("*.yml"):
        workflow = path.read_text(encoding="utf-8")
        if hardcoded_artifact_version.search(workflow):
            findings.append(f"hard-coded asecli artifact version: {path.relative_to(root)}")
        if "shasum -a 256 dist/*.whl dist/*.tar.gz" in workflow:
            findings.append(f"non-portable artifact checksum paths: {path.relative_to(root)}")

    print(json.dumps({"ok": not findings, "findings": findings}, ensure_ascii=False))
    return 0 if not findings else 1


if __name__ == "__main__":
    raise SystemExit(main())
