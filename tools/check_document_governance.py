#!/usr/bin/env python3
"""Repository-local strict checks for traceability and release records."""

from __future__ import annotations

import csv
from pathlib import Path
import re


ID = re.compile(r"\b(?:FR|CR|BUG|MOD|TASK|REG|REL)-[A-Za-z0-9._-]+\b")
SOURCE = re.compile(r"^(?:FR|CR|BUG)-")
COMMIT = re.compile(r"\b[0-9a-f]{7,40}\b", re.IGNORECASE)


def _ids(value: str, prefix: str | None = None) -> set[str]:
    values = set(ID.findall(value))
    return {item for item in values if prefix is None or item.startswith(prefix)}


def _table_links(path: Path, prefix: str, relation_index: int) -> dict[str, set[str]]:
    result: dict[str, set[str]] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        cells = _markdown_cells(line)
        if not cells or not cells[0].startswith(prefix) or len(cells) <= relation_index:
            continue
        result[cells[0]] = _ids(cells[relation_index])
    return result


def _markdown_cells(line: str) -> list[str]:
    if not line.lstrip().startswith("|"):
        return []
    cells: list[str] = []
    current: list[str] = []
    escaped = False
    for char in line.strip().strip("|"):
        if char == "|" and not escaped:
            cells.append("".join(current).strip().replace("\\|", "|"))
            current = []
        else:
            current.append(char)
        escaped = char == "\\" and not escaped
        if char != "\\":
            escaped = False
    cells.append("".join(current).strip().replace("\\|", "|"))
    return cells


def document_governance_findings(root: Path) -> list[str]:
    findings: list[str] = []
    trace = root / "docs/00-governance/traceability.csv"
    module_links = _table_links(root / "docs/01-architecture/module-map.md", "MOD-", 2)
    task_links = _table_links(root / "docs/04-delivery/project-plan-task-charter.md", "TASK-", 1)
    reg_links = _table_links(root / "docs/03-quality/regression-catalog.md", "REG-", 1)

    with trace.open(encoding="utf-8-sig", newline="") as handle:
        for number, row in enumerate(csv.DictReader(handle), start=2):
            source = (row.get("source_id") or "").strip()
            if not SOURCE.match(source):
                continue
            modules = _ids(row.get("module_or_contract") or "", "MOD-")
            if not modules:
                findings.append(f"trace row {number} {source} must reference MOD-*")
            for module in sorted(modules):
                if source not in module_links.get(module, set()):
                    findings.append(f"{module} does not link back to {source}")
            task_value = row.get("task_or_commit") or ""
            tasks = _ids(task_value, "TASK-")
            if not tasks and not COMMIT.search(task_value):
                findings.append(f"trace row {number} {source} needs TASK-* or commit")
            for task in sorted(tasks):
                if source not in task_links.get(task, set()):
                    findings.append(f"{task} does not link back to {source}")
            regs = _ids(row.get("regression_id") or "", "REG-")
            if not regs:
                findings.append(f"trace row {number} {source} must reference REG-*")
            for reg in sorted(regs):
                if source not in reg_links.get(reg, set()):
                    findings.append(f"{reg} does not link back to {source}")

    for line in (root / "docs/04-delivery/project-plan-task-charter.md").read_text(encoding="utf-8").splitlines():
        cells = _markdown_cells(line)
        if cells and cells[0].startswith("TASK-") and len(cells) > 7 and "REG-" not in cells[7]:
            findings.append(f"{cells[0]} verification field must reference REG-*")

    required = {
        "变更集合": ("FR/CR/BUG/ADR", "版本/提交/PR", "兼容性说明"),
        "验证与风险": ("测试/构建/审计证据", "已知风险与监控", "Go / No-Go 决定与负责人"),
        "回滚": ("触发条件", "步骤", "验证"),
    }
    for path in sorted((root / "docs/04-delivery/releases").glob("REL-*.md")):
        text = path.read_text(encoding="utf-8")
        if not re.search(r"^status:\s*released\s*$", text, re.MULTILINE):
            continue
        for section, labels in required.items():
            if not re.search(rf"^##\s+{re.escape(section)}\s*$", text, re.MULTILINE):
                findings.append(f"{path.name} missing section {section}")
            for label in labels:
                if not re.search(rf"^\s*-\s*{re.escape(label)}\s*[:：]", text, re.MULTILINE):
                    findings.append(f"{path.name} missing field {section}/{label}")
    return findings
