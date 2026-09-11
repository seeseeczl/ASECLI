"""Consumer-owned machine-readable contracts shipped with ASECLI."""

from __future__ import annotations

import json
import hashlib
from importlib.resources import files

from .schema_validation import validate_schema


EDITOR_GRAPH_V3 = "contracts/editor-graph-spec.v3.schema.json"
SGCLI_NATIVE_V3_SNAPSHOT = "contracts/sgcli.native.v3.schema.json"
SGCLI_NATIVE_CONSUMER = {
    "package": "sgcli",
    "version": "0.2.0",
    "contract": "sgcli.native.v3",
    "sha256": "b0cee4774e6a3e4a7dfd32ba1c55f8969ee9c7f5f9d48eb4be7649287e817651",
}


def load_editor_graph_schema(version: int = 3) -> dict:
    if version != 3:
        raise ValueError(f"unsupported EditorGraphSpec contract version: {version}")
    resource = files("asecli").joinpath(EDITOR_GRAPH_V3)
    return json.loads(resource.read_text(encoding="utf-8"))


def validate_editor_graph_spec(value: dict, version: int = 3) -> None:
    validate_schema(value, load_editor_graph_schema(version))


def load_sgcli_native_schema_snapshot() -> dict:
    resource = files("asecli").joinpath(SGCLI_NATIVE_V3_SNAPSHOT)
    raw = resource.read_bytes()
    actual = hashlib.sha256(raw).hexdigest()
    expected = SGCLI_NATIVE_CONSUMER["sha256"]
    if actual != expected:
        raise RuntimeError(
            f"sgcli.native.v3 snapshot hash mismatch: expected {expected}, got {actual}"
        )
    return json.loads(raw.decode("utf-8"))


def validate_sgcli_native_spec(value: dict) -> None:
    validate_schema(value, load_sgcli_native_schema_snapshot())
