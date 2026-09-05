#!/usr/bin/env python3
"""Validate that every pytest selector in the REG catalog still collects."""

from __future__ import annotations

import argparse
import json
import re
import shlex
import subprocess
from dataclasses import dataclass
from pathlib import Path


PYTEST_SPAN_RE = re.compile(r"`([^`\r\n]*\bpytest\b[^`\r\n]*)`")
ENV_ASSIGN_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=")


@dataclass(frozen=True)
class CatalogCommand:
    text: str
    pytest_args: tuple[str, ...]
    selectors: tuple[str, ...]
    conditional: bool


def catalog_command_spans(catalog: Path) -> list[str]:
    return PYTEST_SPAN_RE.findall(catalog.read_text(encoding="utf-8"))


def _parse_command(command: str) -> CatalogCommand:
    parts = shlex.split(command)
    for uv_index in range(len(parts) - 2):
        if parts[uv_index : uv_index + 2] != ["uv", "run"]:
            continue
        try:
            pytest_index = parts.index("pytest", uv_index + 2)
        except ValueError:
            continue
        pytest_args = tuple(parts[pytest_index + 1 :])
        selectors = tuple(
            item for item in pytest_args if item.split("::", 1)[0].endswith(".py")
        )
        conditional = any(ENV_ASSIGN_RE.match(item) for item in parts[:uv_index]) or any(
            item == "bridge" and pytest_args[index - 1] in {"-m", "--markexpr"}
            for index, item in enumerate(pytest_args)
            if index > 0
        )
        return CatalogCommand(command, pytest_args, selectors, conditional)
    raise ValueError("pytest code span is not a supported 'uv run ... pytest' command")


def catalog_commands(catalog: Path) -> tuple[list[CatalogCommand], list[dict[str, str]]]:
    commands = []
    failures = []
    for command in catalog_command_spans(catalog):
        try:
            commands.append(_parse_command(command))
        except (ValueError, IndexError) as exc:
            failures.append({"command": command, "detail": str(exc)})
    return commands, failures


def _unique_selectors(commands: list[CatalogCommand]) -> list[str]:
    combined = []
    seen = set()
    for command in commands:
        for selector in command.selectors:
            if selector not in seen:
                seen.add(selector)
                combined.append(selector)
    return combined


def _run_collect(root: Path, selectors: list[str] | tuple[str, ...]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["uv", "run", "--frozen", "pytest", "--collect-only", "-q", *selectors],
        cwd=root,
        capture_output=True,
        text=True,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    root = Path(__file__).resolve().parents[1]
    parser.add_argument("--catalog", type=Path, default=root / "docs/03-quality/regression-catalog.md")
    args = parser.parse_args(argv)

    spans = catalog_command_spans(args.catalog)
    commands, failures = catalog_commands(args.catalog)
    combined = None if failures else _run_collect(root, _unique_selectors(commands))
    if combined is not None and combined.returncode != 0:
        for command in commands:
            proc = _run_collect(root, command.selectors)
            if proc.returncode != 0:
                failures.append(
                    {"command": command.text, "detail": (proc.stdout + proc.stderr)[-800:]}
                )

    payload = {
        "ok": not failures and len(commands) == len(spans),
        "checked": len(spans),
        "parsed": len(commands),
        "conditional": sum(command.conditional for command in commands),
        "missed": len(spans) - len(commands),
        "failures": failures,
    }
    print(json.dumps(payload, ensure_ascii=False))
    return 0 if payload["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
