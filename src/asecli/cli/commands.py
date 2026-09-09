"""Command implementations (TASK-0010). Split from main.py for LOC budget."""

from __future__ import annotations

import os

from ..bridge import McpError
from ..bridge import import_shader_via_mcp, recompile_via_mcp
from ..checks import (
    ChecksumFormatError,
    fix_checksum,
    validate_file,
    verify_checksum,
)
from ..core import (
    AseFile,
    NodeLine,
    connect,
    disconnect,
    node_from_schema,
    parse_node_line,
    require_managed_property_presentation,
    set_node_field,
)
from ..schema import allows_mutation, is_version_compatible, schema_for, schema_version
from .io import (
    UnsafeWritePathError,
    WriteConflictError,
    atomic_write,
    read_text_snapshot,
)
from .recompile_metadata import restore_recompile_metadata, snapshot_recompile_metadata

EXIT_OK = 0
EXIT_ERROR = 2
EXIT_BRIDGE = 3
class CliError(Exception):
    def __init__(self, code: str, message: str, data: dict | None = None):
        super().__init__(message)
        self.code = code
        self.data = data
def _load(path: str) -> AseFile:
    try:
        return AseFile.from_path(path)
    except FileNotFoundError:
        raise CliError("NOT_FOUND", f"file not found: {path}")
    except ValueError as e:
        raise CliError("PARSE_ERROR", str(e))


def _save(ase_file: AseFile, path: str, write: bool) -> dict:
    issues = validate_file(ase_file)
    errors = [issue for issue in issues if issue["severity"] == "error"]
    if errors:
        raise CliError(
            "VALIDATION_ERROR",
            f"mutation would leave {len(errors)} structural error(s)",
            {"issues": issues, "error_count": len(errors)},
        )
    if not write:
        return {"written": False, "preview_bytes": len(ase_file.serialize())}
    try:
        require_managed_property_presentation(ase_file)
    except ValueError as exc:
        raise CliError("PROPERTY_PRESENTATION_ERROR", str(exc)) from exc
    _commit_text(path, ase_file.serialize(), ase_file.source_digest)
    return {"written": True, "path": str(path)}


def _commit_text(path: str, text: str, expected_digest: str | None) -> None:
    try:
        atomic_write(path, text, expected_digest=expected_digest)
    except WriteConflictError as exc:
        raise CliError(
            "WRITE_CONFLICT",
            str(exc),
            {
                "path": str(exc.path),
                "expected": exc.expected[:12] if exc.expected else None,
                "actual": exc.actual[:12] if exc.actual else None,
            },
        ) from exc
    except UnsafeWritePathError as exc:
        raise CliError("UNSAFE_PATH", str(exc)) from exc
    except OSError as exc:
        raise CliError("WRITE_ERROR", str(exc)) from exc


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
    except ValueError as e:
        raise CliError("USAGE_ERROR", str(e))
    saved = _save(f, args.file, args.write)
    return {"node": node.node_id, "field": args.field, "value": args.value, **saved}


def cmd_add_node(args) -> dict:
    f = _load(args.file)
    if args.line is not None:
        parse_node_line(args.line)
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
        if not is_version_compatible(args.type, f.graph.version):
            raise CliError(
                "SCHEMA_VERSION_MISMATCH",
                f"node schema version {schema_version(args.type)} is not compatible with graph version {f.graph.version}",
            )
        node = node_from_schema(f.graph, s, args.id, args.pos, args.type)
    try:
        f.graph.add_node(node)
    except ValueError as e:
        raise CliError("VALIDATION_ERROR", str(e))
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
    except ValueError as e:
        raise CliError("USAGE_ERROR", str(e))
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


def cmd_validate(args) -> dict:
    f = _load(args.file)
    issues = validate_file(f)
    data = {
        "file": args.file,
        "issues": issues,
        "error_count": sum(1 for i in issues if i["severity"] == "error"),
    }
    if data["error_count"]:
        raise CliError(
            "VALIDATION_ERROR",
            f"graph contains {data['error_count']} structural error(s)",
            data,
        )
    return data


def cmd_fix_checksum(args) -> dict:
    try:
        text, source_digest = read_text_snapshot(args.file)
    except FileNotFoundError:
        raise CliError("NOT_FOUND", f"file not found: {args.file}")
    except UnsafeWritePathError as exc:
        raise CliError("UNSAFE_PATH", str(exc)) from exc
    try:
        ok, stored, actual = verify_checksum(text)
        fixed = fix_checksum(text)
    except ChecksumFormatError as exc:
        raise CliError("CHECKSUM_FORMAT_ERROR", str(exc)) from exc
    if args.write:
        _commit_text(args.file, fixed, source_digest)
    return {"was_valid": ok, "stored": stored, "fixed_to": actual, "written": bool(args.write)}


def cmd_recompile(args) -> dict:
    if args.instance_token_argv is not None:
        raise CliError("USAGE_ERROR", "do not pass MCP tokens via argv; use ASECLI_MCP_INSTANCE_TOKEN")
    instance_token = os.environ.get("ASECLI_MCP_INSTANCE_TOKEN")
    metadata_snapshot = snapshot_recompile_metadata(args.file)
    try:
        result = recompile_via_mcp(
            args.file,
            mcp_url=args.mcp_url,
            instance_token=instance_token,
            allow_remote_mcp=args.allow_remote_mcp,
        )
        if metadata_snapshot:
            ase_file, restored = restore_recompile_metadata(args.file, metadata_snapshot)
            output = fix_checksum(ase_file.serialize())
            _commit_text(args.file, output, ase_file.source_digest)
            result["metadata_restored"] = restored
            result["asset_import"] = import_shader_via_mcp(
                args.file, mcp_url=args.mcp_url, instance_token=instance_token,
                allow_remote_mcp=args.allow_remote_mcp,
            )
        return result
    except McpError as e:
        raise CliError("BRIDGE_ERROR", str(e), e.data)
    except FileNotFoundError as e:
        raise CliError("NOT_FOUND", str(e))
    except ValueError as e:
        raise CliError("USAGE_ERROR", str(e))
