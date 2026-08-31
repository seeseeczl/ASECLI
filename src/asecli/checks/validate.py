"""Structural validation (TASK-0008)."""

from __future__ import annotations

from ..core import AseFile
from .checksum import verify_checksum


def validate_file(ase_file: AseFile) -> list[dict]:
    """Return a list of issue dicts. Empty list means the graph is structurally sound."""
    issues: list[dict] = []
    graph = ase_file.graph

    seen: dict[str, int] = {}
    for n in graph.nodes:
        seen[n.node_id] = seen.get(n.node_id, 0) + 1
    for node_id, count in seen.items():
        if count > 1:
            issues.append(
                {"code": "DUPLICATE_NODE_ID", "severity": "error", "node_id": node_id,
                 "message": f"node id {node_id} appears {count} times"}
            )

    node_ids = set(seen)
    for w in graph.wires:
        if w.in_node not in node_ids:
            issues.append(
                {"code": "DANGLING_WIRE", "severity": "error", "node_id": w.in_node,
                 "message": f"wire references missing input node {w.in_node}"}
            )
        if w.out_node not in node_ids:
            issues.append(
                {"code": "DANGLING_WIRE", "severity": "error", "node_id": w.out_node,
                 "message": f"wire references missing output node {w.out_node}"}
            )

    for n in graph.nodes:
        if not n.type_name:
            issues.append(
                {"code": "MALFORMED_NODE", "severity": "error", "node_id": n.node_id,
                 "message": f"node {n.node_id} has empty type"}
            )

    ok, stored, actual = verify_checksum(ase_file.serialize())
    if stored is not None and not ok:
        issues.append(
            {"code": "CHECKSUM_MISMATCH", "severity": "warning",
             "message": f"stored {stored} != computed {actual} (non-blocking: ASE loads anyway)"}
        )
    return issues
