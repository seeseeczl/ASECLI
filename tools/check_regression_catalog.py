#!/usr/bin/env python3
"""Validate that every pytest command in the REG catalog still collects."""

from __future__ import annotations

import argparse
import json
import re
import shlex
import subprocess
from pathlib import Path


COMMAND_RE = re.compile(r"`(uv run pytest [^`]+)`")


def catalog_commands(catalog: Path) -> list[tuple[str, list[str]]]:
    commands = []
    for command in COMMAND_RE.findall(catalog.read_text(encoding="utf-8")):
        parts = shlex.split(command)
        commands.append((command, parts[3:]))
    return commands


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    root = Path(__file__).resolve().parents[1]
    parser.add_argument("--catalog", type=Path, default=root / "docs/03-quality/regression-catalog.md")
    args = parser.parse_args(argv)

    failures = []
    commands = catalog_commands(args.catalog)
    for command, pytest_args in commands:
        proc = subprocess.run(
            ["uv", "run", "--frozen", "pytest", "--collect-only", "-q", *pytest_args],
            cwd=root,
            capture_output=True,
            text=True,
        )
        if proc.returncode != 0:
            failures.append({"command": command, "detail": (proc.stdout + proc.stderr)[-800:]})

    print(json.dumps({"ok": not failures, "checked": len(commands), "failures": failures}, ensure_ascii=False))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
