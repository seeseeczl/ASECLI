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
    "version": "0.3.5",
    "contract": "sgcli.native.v3",
    "sha256": "bb16ce3f61e0772c51bcbfe89cd010ee426db12c59a6e84afad34fd512b41b82",
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
