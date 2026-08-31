"""Command implementations (TASK-0010). Split from main.py for LOC budget."""

from __future__ import annotations

import json
import re
from pathlib import Path

from ..bridge import McpError
from ..bridge import recompile_via_mcp
from ..checks import compute_checksum, fix_checksum, validate_file, verify_checksum
from ..core import (
    AseFile,
    NodeLine,
    _parse_node_line,
    connect,
    disconnect,
    node_from_schema,
    remove_node,
    set_node_field,
    tidy,
)
from ..schema import allows_mutation, schema_for

EXIT_OK = 0
EXIT_ERROR = 2
EXIT_BRIDGE = 3


class CliError(Exception):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


def _load(path: str) -> AseFile:
    try:
        return AseFile.from_path(path)
    except FileNotFoundError:
        raise CliError("NOT_FOUND", f"file not found: {path}")
    except ValueError as e:
        raise CliError("PARSE_ERROR", str(e))


def _save(ase_file: AseFile, path: str, write: bool) -> dict:
    if not write:
        return {"written": False, "preview_bytes": len(ase_file.serialize())}
    atomic_write(path, ase_file.serialize())
    return {"written": True, "path": str(path)}


def atomic_write(path: str, text: str) -> None:
    """Atomic write with .bak backup of previous content (AA-OPS-004)."""
    import os

    target = Path(path)
    if target.exists():
        backup = target.with_suffix(target.suffix + ".bak")
        backup.write_bytes(target.read_bytes())
    tmp = target.with_suffix(target.suffix + ".tmp")
    tmp.write_text(text, encoding="utf-8", newline="")
    os.replace(tmp, target)


def _parse_endpoint(ep: str) -> tuple[str, str]:
    if ":" not in ep:
        raise CliError("USAGE_ERROR", f"endpoint must be node:port, got {ep!r}")
    node, port = ep.split(":", 1)
    return node, port


def cmd_parse(args) -> dict:
    f = _load(args.file)
    g = f.graph
    return {
        "file": args.file,
        "version": g.version,
        "node_count": len(g.nodes),
        "wire_count": len(g.wires),
        "nodes": [{"id": n.node_id, "type": n.type_name, "pos": n.raw_fields[3]} for n in g.nodes],
    }


def cmd_set_field(args) -> dict:
    f = _load(args.file)
    try:
        node = set_node_field(f.graph, args.node, args.field, args.value)
    except (KeyError, IndexError) as e:
        raise CliError("NOT_FOUND", str(e))
    saved = _save(f, args.file, args.write)
    return {"node": node.node_id, "field": args.field, "value": args.value, **saved}


def cmd_add_node(args) -> dict:
    f = _load(args.file)
    if args.line is not None:
        _parse_node_line(args.line)
        fields = args.line.split(";")
        node = NodeLine(type_name=fields[1], node_id=fields[2], raw_fields=fields)
    else:
        if not args.type:
            raise CliError("USAGE_ERROR", "either --type or --line is required")
        s = schema_for(args.type)
        if s is None:
            raise CliError("SCHEMA_UNAVAILABLE", f"unknown node type: {args.type} (use --line to insert raw)")
        if not allows_mutation(args.type):
            raise CliError("SCHEMA_UNAVAILABLE", f"{args.type} has opaque layout; use --line with a real serialized line")
        node = node_from_schema(f.graph, s, args.id, args.pos, args.type)
    f.graph.add_node(node)
    saved = _save(f, args.file, args.write)
    import re as _re

    warnings = []
    if _re.search(r"[0-9a-f]{32}", node.to_line(), _re.IGNORECASE):
        warnings.append(
            "node line contains a 32-hex identifier copied from the schema placeholder; "
            "verify uniqueness in Unity (duplicate guids may conflict)"
        )
    return {"node_id": node.node_id, "type": node.type_name, "warnings": warnings, **saved}


def cmd_connect(args) -> dict:
    f = _load(args.file)
    src, sport = _parse_endpoint(args.src)
    dst, dport = _parse_endpoint(args.dst)
    try:
        wire = connect(f.graph, src, sport, dst, dport)
    except KeyError as e:
        raise CliError("NOT_FOUND", str(e))
    saved = _save(f, args.file, args.write)
    return {"from": args.src, "to": args.dst, "line": wire.to_line(), **saved}


def cmd_disconnect(args) -> dict:
    f = _load(args.file)
    src, sport = _parse_endpoint(args.src)
    dst, dport = _parse_endpoint(args.dst)
    if not disconnect(f.graph, src, sport, dst, dport):
        raise CliError("NOT_FOUND", f"wire {args.src} -> {args.dst} not found")
    saved = _save(f, args.file, args.write)
    return {"removed": True, **saved}


def cmd_remove_node(args) -> dict:
    f = _load(args.file)
    try:
        wires = remove_node(f.graph, args.node)
    except KeyError as e:
        raise CliError("NOT_FOUND", str(e))
    saved = _save(f, args.file, args.write)
    return {"removed_node": args.node, "removed_wires": wires, **saved}


def cmd_validate(args) -> dict:
    f = _load(args.file)
    issues = validate_file(f)
    return {
        "file": args.file,
        "issues": issues,
        "error_count": sum(1 for i in issues if i["severity"] == "error"),
    }


def cmd_fix_checksum(args) -> dict:
    path = Path(args.file)
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        raise CliError("NOT_FOUND", f"file not found: {args.file}")
    ok, stored, actual = verify_checksum(text)
    fixed = fix_checksum(text)
    atomic_write(args.file, fixed)
    return {"was_valid": ok, "stored": stored, "fixed_to": actual, "written": True}


def cmd_layout(args) -> dict:
    f = _load(args.file)
    moved = tidy(f.graph, gap_x=args.gap_x, gap_y=args.gap_y)
    saved = _save(f, args.file, args.write)
    return {"moved": moved, **saved}


def cmd_create(args) -> dict:
    f = _load(args.from_template)
    text = f.serialize()
    if args.name:
        m = re.search(r'Shader "([^"]+)"', text)
        if not m:
            raise CliError("USAGE_ERROR", 'template has no Shader "..." declaration to rename')
        if ";" in args.name:
            raise CliError("USAGE_ERROR", "shader name must not contain ';'")
        text = text.replace(f'Shader "{m.group(1)}"', f'Shader "{args.name}"', 1)
        old = m.group(1)
        if old != args.name:
            # AA-COR-003: also rename delimited occurrences inside the graph data
            text = text.replace(f";{old};", f";{args.name};")
    if args.graph_from:
        donor = _load(args.graph_from)
        begin = text.index("/*ASEBEGIN")
        end = text.index("ASEEND*/", begin)
        text = text[:begin] + donor.prefix.lstrip("\n") + donor.graph.serialize() + text[end:]
    chk = text.find("//CHKSM=")
    if chk >= 0:
        text = text[:chk] + "//CHKSM=" + compute_checksum(text[:chk])
    if Path(args.out).exists() and not args.force:
        raise CliError("USAGE_ERROR", f"{args.out} exists (use --force)")
    atomic_write(args.out, text)
    return {"created": args.out, "name": args.name, "graph_from": args.graph_from}


def cmd_recompile(args) -> dict:
    try:
        return recompile_via_mcp(args.file, mcp_url=args.mcp_url, instance_token=args.instance_token)
    except McpError as e:
        raise CliError("BRIDGE_ERROR", str(e))
    except FileNotFoundError as e:
        raise CliError("NOT_FOUND", str(e))
    except ValueError as e:
        raise CliError("USAGE_ERROR", str(e))
