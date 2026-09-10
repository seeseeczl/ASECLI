"""IO and routing helpers for EditorGraphSpec, split out to bound LOC."""

from __future__ import annotations

import json
from pathlib import Path

from .editor_spec import EditorGraphSpec, SpecError


_ASE_PACKAGE_SCHEMA = "sgcli.ase-package.v1"


def load_editor_graph_spec(path: str | Path) -> EditorGraphSpec:
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise SpecError(f"cannot read EditorGraphSpec JSON: {exc}") from exc
    if isinstance(value, dict) and "graph" in value:
        allowed = {"schema", "graph", "report"}
        unknown = sorted(set(value) - allowed)
        if unknown:
            raise SpecError(f"ASE package has unknown keys: {unknown}")
        if set(value) != {"schema", "graph", "report"}:
            raise SpecError("ASE package requires schema, graph and report")
        if value["schema"] != _ASE_PACKAGE_SCHEMA:
            raise SpecError(f"unsupported ASE package schema: {value['schema']!r}")
        if not isinstance(value["graph"], dict) or not isinstance(value["report"], dict):
            raise SpecError("ASE package graph and report must be objects")
        value = value["graph"]
    return EditorGraphSpec.from_dict(value)


def route_create_backend(requested: str, spec: EditorGraphSpec | None) -> str:
    if requested not in {"text", "editor", "auto"}:
        raise SpecError(f"unknown create backend: {requested}")
    if requested == "auto":
        return "editor" if spec is not None else "text"
    return requested
