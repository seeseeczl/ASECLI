#!/usr/bin/env python3
"""Fail closed when a release tag does not match the project version."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re


VERSION_LINE = re.compile(r'^version\s*=\s*"([0-9]+\.[0-9]+\.[0-9]+)"\s*$', re.MULTILINE)
SEMVER_TAG = re.compile(r"^v([0-9]+\.[0-9]+\.[0-9]+)$")


def project_version(pyproject: Path) -> str:
    match = VERSION_LINE.search(pyproject.read_text(encoding="utf-8"))
    if match is None:
        raise ValueError("pyproject.toml must declare a strict X.Y.Z project version")
    return match.group(1)


def candidate_findings(tag: str, version: str) -> list[str]:
    match = SEMVER_TAG.fullmatch(tag)
    if match is None:
        return [f"release tag must match vX.Y.Z, got {tag!r}"]
    if match.group(1) != version:
        return [f"release tag {tag!r} does not match project version {version!r}"]
    return []


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tag", default=os.environ.get("GITHUB_REF_NAME", ""))
    parser.add_argument("--pyproject", type=Path, default=Path("pyproject.toml"))
    args = parser.parse_args()

    try:
        version = project_version(args.pyproject)
        findings = candidate_findings(args.tag, version)
    except (OSError, UnicodeError, ValueError) as exc:
        version = None
        findings = [str(exc)]
    print(json.dumps({"ok": not findings, "tag": args.tag, "version": version,
                      "findings": findings}, ensure_ascii=False))
    return 0 if not findings else 1


if __name__ == "__main__":
    raise SystemExit(main())
