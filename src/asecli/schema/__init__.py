"""Node schema library (TASK-0005)."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

DATA = Path(__file__).parent / "data" / "schemas.json"


@lru_cache(maxsize=1)
def load() -> dict:
    return json.loads(DATA.read_text(encoding="utf-8"))


def schema_for(node_type: str) -> dict | None:
    """Return the schema for a node type, or None when unknown (caller passthrough)."""
    return load()["types"].get(node_type)


def is_known(node_type: str) -> bool:
    s = schema_for(node_type)
    return s is not None and s.get("source") in ("runtime", "observed")


def allows_mutation(node_type: str) -> bool:
    """Runtime types: full structured mutation. Observed types: full-line replace only."""
    s = schema_for(node_type)
    return (
        s is not None
        and s.get("source") == "runtime"
        and s.get("layout_ok") is True
    )


def schema_version(node_type: str) -> str | None:
    """Return the normalized ASE version for a runtime schema."""
    schema = schema_for(node_type)
    value = schema.get("ase_version") if schema else None
    if not isinstance(value, str) or not value:
        return None
    return value.removeprefix("Version=")


def is_version_compatible(node_type: str, graph_version: str) -> bool:
    """Only exact runtime schema versions are proven safe for structured writes."""
    version = schema_version(node_type)
    return version is not None and version == graph_version.removeprefix("Version=")
