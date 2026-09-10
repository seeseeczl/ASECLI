"""IO and routing helpers for EditorGraphSpec, split out to bound LOC."""

from __future__ import annotations

import json
from pathlib import Path

from .editor_spec import EditorGraphSpec, SpecError


def load_editor_graph_spec(path: str | Path) -> EditorGraphSpec:
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise SpecError(f"cannot read EditorGraphSpec JSON: {exc}") from exc
    return EditorGraphSpec.from_dict(value)


def route_create_backend(requested: str, spec: EditorGraphSpec | None) -> str:
    if requested not in {"text", "editor", "auto"}:
        raise SpecError(f"unknown create backend: {requested}")
    if requested == "auto":
        return "editor" if spec is not None else "text"
    return requested
