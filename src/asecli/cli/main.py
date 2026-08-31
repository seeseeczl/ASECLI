"""asecli CLI entry point (TASK-0010): every command emits JSON on stdout."""

from __future__ import annotations

import argparse
import json
import sys

from .commands import EXIT_BRIDGE, EXIT_ERROR, EXIT_OK, CliError
from .commands import (
    cmd_add_node,
    cmd_connect,
    cmd_create,
    cmd_disconnect,
    cmd_fix_checksum,
    cmd_layout,
    cmd_parse,
    cmd_recompile,
    cmd_remove_node,
    cmd_set_field,
    cmd_validate,
)


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
