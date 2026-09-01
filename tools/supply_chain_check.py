#!/usr/bin/env python3
"""Offline integrity, action pinning, license, and high-confidence secret checks."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


SECRET_PATTERNS = {
    "private-key": re.compile(r"-----BEGIN (?:RSA |OPENSSH |EC |DSA )?PRIVATE KEY-----"),
    "github-token": re.compile(r"\bgh[pousr]_[A-Za-z0-9]{36,}\b"),
    "openai-key": re.compile(r"\bsk-[A-Za-z0-9]{32,}\b"),
    "aws-access-key": re.compile(r"\bAKIA[A-Z0-9]{16}\b"),
}
PINNED_ACTION = re.compile(r"^\s*-?\s*uses:\s*[^\s@]+@[0-9a-f]{40}(?:\s*#.*)?$", re.MULTILINE)
ANY_ACTION = re.compile(r"^\s*-?\s*uses:\s*[^\s@]+@[^\s#]+", re.MULTILINE)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    root = Path(__file__).resolve().parents[1]
    findings = []

    if not (root / "LICENSE").is_file():
        findings.append("LICENSE is missing")

    lock = (root / "uv.lock").read_text(encoding="utf-8")
    for block in lock.split("[[package]]")[1:]:
        if "registry =" in block and "hash = \"sha256:" not in block:
            name = re.search(r'name = "([^"]+)"', block)
            findings.append(f"registry package lacks sha256: {name.group(1) if name else 'unknown'}")

    for workflow in (root / ".github/workflows").glob("*.yml"):
        text = workflow.read_text(encoding="utf-8")
        if len(ANY_ACTION.findall(text)) != len(PINNED_ACTION.findall(text)):
            findings.append(f"un-pinned action in {workflow.relative_to(root)}")

    scan_suffixes = {".py", ".md", ".yml", ".yaml", ".toml", ".json", ".csv"}
    excluded = {".git", ".venv", "dist", "build-a", "build-b"}
    for path in root.rglob("*"):
        if not path.is_file() or path.suffix not in scan_suffixes or any(part in excluded for part in path.parts):
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        for label, pattern in SECRET_PATTERNS.items():
            if pattern.search(text):
                findings.append(f"possible {label}: {path.relative_to(root)}")

    result = {
        "ok": not findings,
        "findings": findings,
        "runtime_dependencies": 0,
        "lock_integrity": "checked",
        "vulnerability_database": "not-run-offline; requires real CI/Dependabot evidence",
    }
    rendered = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
