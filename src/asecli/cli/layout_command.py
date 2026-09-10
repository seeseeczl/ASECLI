"""CLI composition for legacy and editor-accurate meticulous layout."""

from __future__ import annotations

import hashlib
import argparse
import json
import math
import os

from ..bridge import McpError, apply_wire_routes_via_mcp, inspect_graph_geometry_via_mcp
from ..checks import fix_checksum, validate_file
from ..core import (
    AseFile,
    COMMENTARY_TYPE,
    WIRE_NODE_TYPE,
    apply_meticulous_layout,
    audit_meticulous_layout,
    govern_comment_purposes,
    meticulous_layout_positions,
    logical_wire_manifest,
    refit_comments_for_layout,
    require_managed_property_presentation,
    tidy,
)
from .commands import CliError, _commit_text, _load, _save
from .io import restore_from_backup


def configure_layout_parser(sub):
    s = sub.add_parser("layout", help="auto-arrange nodes using legacy or meticulous DAG layout")
    s.add_argument("file")
    s.add_argument("--mode", choices=("legacy", "meticulous"), default="legacy")
    s.add_argument("--audit", action="store_true", help="report meticulous layout quality without writing")
    s.add_argument("--island-columns", type=int, choices=range(1, 9), default=1,
                   help="pack physical calculation islands into columns after recursive fishbone layout")
    s.add_argument("--route-wires", action="store_true",
                   help="explicitly allow meticulous mode to move or add WireNode routing anchors")
    s.add_argument("--gap-x", type=float, default=280.0)
    s.add_argument("--gap-y", type=float, default=120.0)
    s.add_argument("--mcp-url", default="http://127.0.0.1:8080/mcp")
    s.add_argument("--unity-instance", help="target Name@hash when multiple Unity/Tuanjie instances are connected")
    s.add_argument("--allow-remote-mcp", action="store_true")
    s.add_argument("--instance-token", dest="instance_token_argv", help=argparse.SUPPRESS)
    s.add_argument("--write", action="store_true")
    s.set_defaults(func=cmd_layout)


def cmd_layout(args) -> dict:
    if not math.isfinite(args.gap_x) or not math.isfinite(args.gap_y):
        raise CliError("USAGE_ERROR", "--gap-x/--gap-y must be finite numbers")
    if args.mode == "legacy":
        if getattr(args, "island_columns", 1) != 1:
            raise CliError("USAGE_ERROR", "--island-columns requires --mode meticulous")
        if args.route_wires:
            raise CliError("USAGE_ERROR", "--route-wires requires --mode meticulous")
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
        plan = meticulous_layout_positions(
            f.graph, geometry, route_wires=args.route_wires,
            island_columns=getattr(args, "island_columns", 1),
        )
        moved = apply_meticulous_layout(f.graph, plan)
        # Audit/dry-run reports a proposed title without mutating the in-memory
        # graph.  Only an explicitly authorized write may persist the title.
        comment_purpose = govern_comment_purposes(f.graph, geometry, apply=bool(args.write))
        comment_changes = refit_comments_for_layout(f.graph, geometry, plan.positions)
        report = audit_meticulous_layout(
            f.graph, geometry, plan, moved=moved, comment_purpose=comment_purpose,
        )
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
    route_transaction = None
    if args.write:
        try:
            require_managed_property_presentation(f)
        except ValueError as exc:
            raise CliError("PROPERTY_PRESENTATION_ERROR", str(exc)) from exc
        _commit_text(args.file, output, f.source_digest)
        if args.route_wires and plan.wire_route_changes:
            expected_manifest = logical_wire_manifest(f.graph)
            expected_semantics = _routed_semantic_fingerprint(f.graph)
            try:
                route_transaction = apply_wire_routes_via_mcp(
                    args.file,
                    plan.wire_route_changes,
                    mcp_url=args.mcp_url,
                    instance_token=os.environ.get("ASECLI_MCP_INSTANCE_TOKEN"),
                    unity_instance=args.unity_instance,
                    allow_remote_mcp=args.allow_remote_mcp,
                )
                persisted = AseFile.from_path(args.file)
                if logical_wire_manifest(persisted.graph) != expected_manifest:
                    raise ValueError("WireNode routing changed the logical connection set")
                if _routed_semantic_fingerprint(persisted.graph) != expected_semantics:
                    raise ValueError("WireNode routing changed non-layout node semantics")
                created = {str(value) for value in route_transaction["created_node_ids"]}
                if any(
                    persisted.graph.node_by_id(node_id) is None
                    or persisted.graph.node_by_id(node_id).type_name != WIRE_NODE_TYPE
                    for node_id in created
                ):
                    raise ValueError("WireNode routing created-node manifest does not match the saved graph")
                post_errors = [
                    item for item in validate_file(persisted) if item["severity"] == "error"
                ]
                if post_errors:
                    raise ValueError(f"WireNode routing left {len(post_errors)} structural error(s)")
            except (McpError, FileNotFoundError, KeyError, ValueError) as exc:
                try:
                    restore_from_backup(args.file)
                except OSError as restore_exc:
                    raise CliError(
                        "WRITE_ERROR",
                        f"WireNode routing failed and backup restore failed: {restore_exc}",
                        {"route_error": str(exc), "recovery": "failed"},
                    ) from restore_exc
                code = "BRIDGE_ERROR" if isinstance(exc, (McpError, FileNotFoundError)) else "LAYOUT_ERROR"
                data = getattr(exc, "data", None) if isinstance(exc, McpError) else None
                raise CliError(
                    code, f"WireNode routing failed; original file restored: {exc}",
                    {**(data or {}), "written": False, "recovery": "restored_from_backup"},
                ) from exc
    return {
        "file": args.file,
        "mode": "meticulous",
        "measurement": "live_ase_geometry_v3",
        "moved": moved,
        "comment_changes": comment_changes,
        "comment_changed_count": len(comment_changes),
        "comment_purpose": comment_purpose,
        "route_wires": bool(args.route_wires),
        "islands": list(plan.islands),
        "wire_route_transaction": route_transaction,
        "audit_only": bool(args.audit),
        "audit": report,
        "written": bool(args.write),
        "path": args.file if args.write else None,
        "preview_bytes": os.path.getsize(args.file) if args.write else len(output),
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
            try:
                fields[10 + int(fields[9])] = "<title>"
            except (IndexError, ValueError):
                pass
        nodes.append(fields)
    payload = {
        "nodes": nodes,
        "wires": sorted((wire.out_node, wire.out_port, wire.in_node, wire.in_port) for wire in graph.wires),
        "other": [raw for kind, raw in graph.instructions if kind == "other"],
    }
    return hashlib.sha256(json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode()).hexdigest()


def _routed_semantic_fingerprint(graph) -> str:
    """Ignore routing anchors/positions while protecting all algorithm data."""
    nodes = []
    for node in graph.nodes:
        if node.type_name == WIRE_NODE_TYPE:
            continue
        fields = list(node.raw_fields)
        fields[3] = "<position>"
        if node.type_name == COMMENTARY_TYPE:
            fields[6], fields[7] = "<width>", "<height>"
            try:
                fields[10 + int(fields[9])] = "<title>"
            except (IndexError, ValueError):
                pass
        nodes.append(fields)
    payload = {
        "nodes": nodes,
        "logical_wires": logical_wire_manifest(graph),
        "other": [raw for kind, raw in graph.instructions if kind == "other"],
    }
    return hashlib.sha256(
        json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode()
    ).hexdigest()
