"""asecli CLI entry point (TASK-0010): every command emits JSON on stdout."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

from ..bridge.mcp_client import McpError
from ..bridge.recompile import recompile_via_mcp
from ..checks import compute_checksum, fix_checksum, validate_file, verify_checksum
from ..core import AseFile, NodeLine
from ..core.model import _parse_node_line
from ..core.graph_ops import connect, disconnect, node_from_schema, remove_node, set_node_field
from ..core.layout import tidy
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
    Path(path).write_text(ase_file.serialize(), encoding="utf-8")
    return {"written": True, "path": str(path)}


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
    return {"node_id": node.node_id, "type": node.type_name, **saved}


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
    path.write_text(fixed, encoding="utf-8")
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
        text = text.replace(f'Shader "{m.group(1)}"', f'Shader "{args.name}"', 1)
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
    Path(args.out).write_text(text, encoding="utf-8")
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


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="asecli", description="Agent-native CLI for Amplify Shader Editor assets")
    sub = p.add_subparsers(dest="command", required=True)

    s = sub.add_parser("parse", help="parse ASE file and print graph summary")
    s.add_argument("file")
    s.set_defaults(func=cmd_parse)

    s = sub.add_parser("set-field", help="set one serialized field of a node")
    s.add_argument("file")
    s.add_argument("--node", required=True)
    s.add_argument("--field", type=int, required=True)
    s.add_argument("--value", required=True)
    s.add_argument("--write", action="store_true")
    s.set_defaults(func=cmd_set_field)

    s = sub.add_parser("add-node", help="add a node (schema-driven, or raw via --line)")
    s.add_argument("file")
    s.add_argument("--type")
    s.add_argument("--id", type=int)
    s.add_argument("--pos", default="0,0")
    s.add_argument("--line", help="raw serialized Node;... line")
    s.add_argument("--write", action="store_true")
    s.set_defaults(func=cmd_add_node)

    s = sub.add_parser("connect", help="wire source output port to destination input port")
    s.add_argument("file")
    s.add_argument("--from", dest="src", required=True, help="source node:port")
    s.add_argument("--to", dest="dst", required=True, help="destination node:port")
    s.add_argument("--write", action="store_true")
    s.set_defaults(func=cmd_connect)

    s = sub.add_parser("disconnect", help="remove a wire")
    s.add_argument("file")
    s.add_argument("--from", dest="src", required=True)
    s.add_argument("--to", dest="dst", required=True)
    s.add_argument("--write", action="store_true")
    s.set_defaults(func=cmd_disconnect)

    s = sub.add_parser("remove-node", help="remove node and attached wires")
    s.add_argument("file")
    s.add_argument("--node", required=True)
    s.add_argument("--write", action="store_true")
    s.set_defaults(func=cmd_remove_node)

    s = sub.add_parser("validate", help="validate graph structure")
    s.add_argument("file")
    s.set_defaults(func=cmd_validate)

    s = sub.add_parser("fix-checksum", help="recompute //CHKSM")
    s.add_argument("file")
    s.set_defaults(func=cmd_fix_checksum)

    s = sub.add_parser("layout", help="auto-arrange node positions (tidy)")
    s.add_argument("file")
    s.add_argument("--gap-x", type=float, default=280.0)
    s.add_argument("--gap-y", type=float, default=120.0)
    s.add_argument("--write", action="store_true")
    s.set_defaults(func=cmd_layout)

    s = sub.add_parser("create", help="create new shader from a compiled template shell")
    s.add_argument("out")
    s.add_argument("--from", dest="from_template", required=True)
    s.add_argument("--name")
    s.add_argument("--graph-from", help="donor ASE file whose graph is injected")
    s.add_argument("--force", action="store_true")
    s.set_defaults(func=cmd_create)

    s = sub.add_parser("recompile", help="trigger ASE regeneration inside running editor (MCP)")
    s.add_argument("file")
    s.add_argument("--mcp-url", default="http://127.0.0.1:8080/mcp")
    s.add_argument("--instance-token", default=None)
    s.set_defaults(func=cmd_recompile)
    return p


def app(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        data = args.func(args)
    except CliError as e:
        json.dump({"ok": False, "error": {"code": e.code, "message": str(e)}}, sys.stdout, ensure_ascii=False)
        sys.stdout.write("\n")
        return EXIT_BRIDGE if e.code == "BRIDGE_ERROR" else EXIT_ERROR
    except Exception as e:  # noqa: BLE001
        json.dump({"ok": False, "error": {"code": "INTERNAL", "message": f"{type(e).__name__}: {e}"}}, sys.stdout, ensure_ascii=False)
        sys.stdout.write("\n")
        return EXIT_ERROR
    json.dump({"ok": True, "data": data}, sys.stdout, ensure_ascii=False)
    sys.stdout.write("\n")
    return EXIT_OK


if __name__ == "__main__":
    raise SystemExit(app())
