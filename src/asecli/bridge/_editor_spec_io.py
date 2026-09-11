"""IO and routing helpers for EditorGraphSpec, split out to bound LOC."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from ..contracts import validate_editor_graph_spec
from ..schema_validation import SchemaValidationError
from .editor_spec import EditorGraphSpec, SpecError


def load_editor_graph_spec_with_sha256(path: str | Path) -> tuple[EditorGraphSpec, str]:
    source = Path(path)
    if source.name.endswith((
        ".asecli-to-sgcli.spec.json",
        ".asecli-to-sgcli.report.json",
    )):
        raise SpecError(
            "ASECLI cannot consume an ASECLI-to-SGCLI artifact"
        )
    try:
        raw = source.read_bytes()
        value = json.loads(raw.decode("utf-8"))
    except FileNotFoundError:
        raise
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise SpecError(f"cannot read EditorGraphSpec JSON: {exc}") from exc
    if isinstance(value, dict) and value.get("version") == 3:
        try:
            validate_editor_graph_spec(value, 3)
        except SchemaValidationError as exc:
            raise SpecError(f"EditorGraphSpec v3 schema validation failed: {exc}") from exc
    return EditorGraphSpec.from_dict(value), hashlib.sha256(raw).hexdigest()


def load_editor_graph_spec(path: str | Path) -> EditorGraphSpec:
    return load_editor_graph_spec_with_sha256(path)[0]


def route_create_backend(requested: str, spec: EditorGraphSpec | None) -> str:
    if requested not in {"text", "editor", "auto"}:
        raise SpecError(f"unknown create backend: {requested}")
    if requested == "auto":
        return "editor" if spec is not None else "text"
    return requested
