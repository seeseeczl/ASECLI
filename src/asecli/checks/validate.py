"""Structural validation (TASK-0008)."""

from __future__ import annotations

from ..core import (
    AseFile,
    COMMENTARY_TYPE,
    parse_commentary_node,
)
from .checksum import ChecksumFormatError, verify_checksum
from .local_vars import append_local_var_issues


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
    input_sources: dict[tuple[str, str], list[tuple[str, str]]] = {}
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
        input_sources.setdefault((w.in_node, w.in_port), []).append((w.out_node, w.out_port))

    for (node_id, port), sources in input_sources.items():
        unique_sources = sorted(set(sources))
        if len(unique_sources) > 1:
            rendered = ", ".join(f"{node}:{source_port}" for node, source_port in unique_sources)
            issues.append(
                {
                    "code": "MULTIPLE_INPUT_CONNECTIONS",
                    "severity": "error",
                    "node_id": node_id,
                    "port": port,
                    "message": f"input {node_id}:{port} has multiple sources: {rendered}",
                }
            )

    for n in graph.nodes:
        if not n.type_name:
            issues.append(
                {"code": "MALFORMED_NODE", "severity": "error", "node_id": n.node_id,
                 "message": f"node {n.node_id} has empty type"}
            )

    append_local_var_issues(graph, issues)

    comment_children: dict[str, list[str]] = {}
    comment_parent: dict[str, str] = {}
    for n in graph.nodes:
        if n.type_name != COMMENTARY_TYPE:
            continue
        try:
            group = parse_commentary_node(n)
        except ValueError as exc:
            issues.append(
                {"code": "MALFORMED_COMMENT", "severity": "error", "node_id": n.node_id,
                 "message": str(exc)}
            )
            continue
        comment_children[n.node_id] = [member for member in group["members"] if member in node_ids]
        for member in group["members"]:
            if member not in node_ids:
                issues.append(
                    {"code": "DANGLING_COMMENT_MEMBER", "severity": "error", "node_id": n.node_id,
                     "message": f"comment {n.node_id} references missing member node {member}"}
                )
            elif member in comment_parent:
                issues.append(
                    {"code": "MULTIPLE_COMMENT_PARENTS", "severity": "error", "node_id": member,
                     "message": f"node {member} belongs to comments {comment_parent[member]} and {n.node_id}"}
                )
            else:
                comment_parent[member] = n.node_id

    visiting: set[str] = set()
    visited: set[str] = set()

    def visit_comment(node_id: str) -> None:
        if node_id in visiting:
            issues.append(
                {"code": "COMMENT_MEMBERSHIP_CYCLE", "severity": "error", "node_id": node_id,
                 "message": f"comment membership contains a cycle at node {node_id}"}
            )
            return
        if node_id in visited:
            return
        visiting.add(node_id)
        for member in comment_children.get(node_id, []):
            if member in comment_children:
                visit_comment(member)
        visiting.remove(node_id)
        visited.add(node_id)

    for comment_id in comment_children:
        visit_comment(comment_id)

    try:
        ok, stored, actual = verify_checksum(ase_file.serialize())
    except ChecksumFormatError as exc:
        issues.append(
            {"code": "CHECKSUM_FORMAT", "severity": "error", "message": str(exc)}
        )
        return issues
    if stored is not None and not ok:
        issues.append(
            {"code": "CHECKSUM_MISMATCH", "severity": "warning",
             "message": f"stored {stored} != computed {actual} (non-blocking: ASE loads anyway)"}
        )
    return issues
