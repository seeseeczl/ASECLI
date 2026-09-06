"""CLI composition for legacy and editor-accurate meticulous layout."""

from __future__ import annotations

import hashlib
import json
import os

from ..bridge import McpError, inspect_graph_geometry_via_mcp
from ..checks import fix_checksum, validate_file
from ..core import (
    apply_meticulous_layout,
    audit_meticulous_layout,
    meticulous_layout_positions,
    refit_comments_for_layout,
    require_managed_property_presentation,
    tidy,
)
from ..core.commentary import COMMENTARY_TYPE
from .commands import CliError, _commit_text, _load, _save


def cmd_layout(args) -> dict:
    if args.mode == "legacy":
        if args.audit:
            raise CliError("USAGE_ERROR", "--audit requires --mode meticulous")
        f = _load(args.file)
        try:
            moved = tidy(f.graph, gap_x=args.gap_x, gap_y=args.gap_y)
        except ValueError as exc:
            raise CliError("LAYOUT_ERROR", str(exc)) from exc
        saved = _save(f, args.file, args.write)
        return {
            "mode": "legacy", "moved": moved, "structural_validation": "passed",
            "visual_validation": "pending", **saved,
        }
    if args.audit and args.write:
        raise CliError("USAGE_ERROR", "--audit is read-only and cannot be combined with --write")
    if args.gap_x != 280.0 or args.gap_y != 120.0:
        raise CliError("USAGE_ERROR", "--gap-x/--gap-y apply only to --mode legacy")
    if args.instance_token_argv is not None:
        raise CliError("USAGE_ERROR", "do not pass MCP tokens via argv; use ASECLI_MCP_INSTANCE_TOKEN")
    return _meticulous(args)


def _meticulous(args) -> dict:
    f = _load(args.file)
    before_semantics = _semantic_fingerprint(f.graph)
    try:
        geometry = inspect_graph_geometry_via_mcp(
            args.file,
            mcp_url=args.mcp_url,
            instance_token=os.environ.get("ASECLI_MCP_INSTANCE_TOKEN"),
            unity_instance=args.unity_instance,
            allow_remote_mcp=args.allow_remote_mcp,
        )
        plan = meticulous_layout_positions(f.graph, geometry)
        moved = apply_meticulous_layout(f.graph, plan)
        comment_changes = refit_comments_for_layout(f.graph, geometry, plan.positions)
        report = audit_meticulous_layout(f.graph, geometry, plan, moved=moved)
    except McpError as exc:
        raise CliError("BRIDGE_ERROR", str(exc), exc.data) from exc
    except FileNotFoundError as exc:
        raise CliError("NOT_FOUND", str(exc)) from exc
    except (KeyError, ValueError) as exc:
        raise CliError("LAYOUT_ERROR", str(exc)) from exc

    after_semantics = _semantic_fingerprint(f.graph)
    if before_semantics != after_semantics:
        raise CliError("LAYOUT_ERROR", "meticulous layout changed graph semantics; refusing output")
    issues = validate_file(f)
    structural_errors = [item for item in issues if item["severity"] == "error"]
    if structural_errors:
        raise CliError(
            "VALIDATION_ERROR",
            f"layout would leave {len(structural_errors)} structural error(s)",
            {"issues": issues, "error_count": len(structural_errors)},
        )
    if args.write and report["hard_failures"]:
        raise CliError(
            "LAYOUT_ERROR",
            f"meticulous layout failed {len(report['hard_failures'])} hard gate(s); file was not written",
            {"audit": report, "written": False},
        )
    output = fix_checksum(f.serialize())
    if args.write:
        try:
            require_managed_property_presentation(f)
        except ValueError as exc:
            raise CliError("PROPERTY_PRESENTATION_ERROR", str(exc)) from exc
        _commit_text(args.file, output, f.source_digest)
    return {
        "file": args.file,
        "mode": "meticulous",
        "measurement": "live_ase_geometry_v2",
        "moved": moved,
        "comment_changes": comment_changes,
        "comment_changed_count": len(comment_changes),
        "audit_only": bool(args.audit),
        "audit": report,
        "written": bool(args.write),
        "path": args.file if args.write else None,
        "preview_bytes": len(output),
        "checksum_recomputed": True,
        "structural_validation": "passed",
        "visual_validation": report["visual_validation"],
        "requires_editor_reload": bool(args.write),
    }


def _semantic_fingerprint(graph) -> str:
    nodes = []
    for node in graph.nodes:
        fields = list(node.raw_fields)
        fields[3] = "<position>"
        if node.type_name == COMMENTARY_TYPE:
            fields[6], fields[7] = "<width>", "<height>"
        nodes.append(fields)
    payload = {
        "nodes": nodes,
        "wires": sorted((wire.out_node, wire.out_port, wire.in_node, wire.in_port) for wire in graph.wires),
        "other": [raw for kind, raw in graph.instructions if kind == "other"],
    }
    return hashlib.sha256(json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode()).hexdigest()
