"""Shared model and constants for ASE -> SG export."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import math
from pathlib import Path
import re
from typing import Any

from .. import __version__

REPORT_SCHEMA = "sgcli.shader-conversion-report.v1"
MAPPING_VERSION = 3
SUPPORTED_ASE_VERSIONS = frozenset({"19109", "19602"})
MASTER_TYPE = "AmplifyShaderEditor.TemplateMultiPassMasterNode"
WIRE_TYPE = "AmplifyShaderEditor.WireNode"
URP_UNLIT_GUID = "2992e84f91cbeb14eab234972e07ea9d"
URP_UNLIT_PASSES = frozenset({
    "ExtraPrePass", "Forward", "ShadowCaster", "DepthOnly", "Meta", "Universal2D",
    "SceneSelectionPass", "ScenePickingPass", "DepthNormals", "DepthNormalsOnly",
})
MASTER_OUTPUTS = {
    0: "SurfaceDescription.BakedGI", 1: "SurfaceDescription.Emission",
    2: "SurfaceDescription.BaseColor", 3: "SurfaceDescription.Alpha",
    4: "SurfaceDescription.AlphaClipThreshold", 5: "VertexDescription.Position",
    6: "VertexDescription.Normal", 7: "SurfaceDescription.AlphaClipThresholdShadow",
}


class ExportError(ValueError):
    def __init__(self, message: str, report: dict[str, Any]):
        super().__init__(message)
        self.report = report


@dataclass
class SemanticNode:
    source_id: str
    target_id: str
    target_type: str
    position: list[float]
    input_names: dict[int, str] = field(default_factory=dict)
    output_names: dict[int, str] = field(default_factory=dict)
    defaults: dict[int, Any] = field(default_factory=dict)
    settings: dict[str, Any] = field(default_factory=dict)
    property_name: str | None = None
    function: dict[str, Any] | None = None
    source_ids: list[str] = field(default_factory=list)

    def candidate(self) -> dict[str, Any]:
        row: dict[str, Any] = {"id": self.target_id, "type": self.target_type, "position": self.position}
        if self.settings:
            row["settings"] = self.settings
        if self.property_name is not None:
            row["property"] = self.property_name
        if self.function is not None:
            row["function"] = self.function
        return row


@dataclass(frozen=True)
class SemanticEdge:
    source_id: str
    source_port: int
    target_id: str
    target_port: int


def report_template(source: Path, target: Path, version: str, source_raw: bytes) -> dict[str, Any]:
    empty = status("not_run", "not run")
    return {
        "schema": REPORT_SCHEMA,
        "exporter": {"name": "asecli", "version": __version__},
        "source": {"path": str(source), "sha256": hashlib.sha256(source_raw).hexdigest(), "ase_version": version},
        "target_environment": {"project": str(target), "doctor": None},
        "mapping_version": MAPPING_VERSION,
        "receiver_schema": {"name": "sgcli.native.v3", "path": None, "sha256": None},
        "source_validation": {"error_count": 0, "warning_count": 0, "issues": []},
        "mappings": [], "dependencies": [], "degradations": [], "diagnostics": [],
        "equivalence": {"status": "not_proven", "reason": "effect validation has not run"},
        "verification": {
            "source_parse": dict(empty), "source_structure": dict(empty),
            "semantic_mapping": dict(empty), "schema": dict(empty),
            "python_precheck": dict(empty), "target_capabilities": dict(empty), "create_preview": dict(empty),
            "actual_create": dict(empty), "save_reload": dict(empty), "compile": dict(empty),
            "canvas": dict(empty), "effect": dict(empty),
        },
    }


def diagnostic(node_id, code, reason, impact):
    return {"source_node_id": node_id, "code": code, "reason": reason, "impact": impact}


def status(state: str, evidence: Any):
    return {"status": state, "evidence": evidence}


def finite(value: Any) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"invalid numeric value {value!r}") from exc
    if not math.isfinite(result):
        raise ValueError(f"non-finite numeric value {value!r}")
    return result


def numbers(value: str, width: int) -> list[float]:
    items = [item.strip() for item in value.strip().strip("()").split(",")]
    if len(items) != width:
        raise ValueError(f"expected {width} components, got {value!r}")
    return [finite(item) for item in items]


def position(node) -> list[float]:
    try:
        x, y = node.raw_fields[3].split(",", 1)
        return [finite(x), finite(y)]
    except (IndexError, ValueError) as exc:
        raise ValueError(f"node {node.node_id} has invalid position") from exc


def normalize(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", value.lower())
