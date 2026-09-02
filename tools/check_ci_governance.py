#!/usr/bin/env python3
"""Dependency-free CI subset of the local Project Architect strict gate."""

from __future__ import annotations

import json
import re
from pathlib import Path


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    config = json.loads((root / ".project-architect.json").read_text(encoding="utf-8"))
    limit = config["loc_thresholds"]["source"]["warning"]
    findings = []

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

    private_core_import = re.compile(r"from\s+\.\.core\s+import\s+[^\n]*\b_\w+")
    for path in (root / "src/asecli").rglob("*.py"):
        if private_core_import.search(path.read_text(encoding="utf-8")):
            findings.append(f"private core import: {path.relative_to(root)}")

    hardcoded_artifact_version = re.compile(r"asecli-\d+\.\d+\.\d+")
    for path in (root / ".github/workflows").glob("*.yml"):
        if hardcoded_artifact_version.search(path.read_text(encoding="utf-8")):
            findings.append(f"hard-coded asecli artifact version: {path.relative_to(root)}")

    print(json.dumps({"ok": not findings, "findings": findings}, ensure_ascii=False))
    return 0 if not findings else 1


if __name__ == "__main__":
    raise SystemExit(main())
