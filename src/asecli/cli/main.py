"""asecli CLI entry point (TASK-0010): every command emits JSON on stdout."""

from __future__ import annotations

import argparse
import json
import os
import sys

from .. import __version__
from ..core import ENABLE_IF_OPERATORS
from .commands import EXIT_BRIDGE, EXIT_ERROR, EXIT_OK, CliError
from .commands import (
    cmd_add_node,
    cmd_connect,
    cmd_disconnect,
    cmd_fix_checksum,
    cmd_layout,
    cmd_parse,
    cmd_recompile,
    cmd_set_field,
    cmd_validate,
)
from .create_command import cmd_create
from .custom_gui_command import cmd_custom_gui
from .gui_support_command import cmd_gui_support
from .commentary_command import cmd_comment_group
from .skill_command import cmd_install_skill
from .usage_command import cmd_graph_audit, cmd_remove_node


class JsonArgumentParser(argparse.ArgumentParser):
    """Keep argparse diagnostics on stderr while routing failures through JSON."""

    def error(self, message: str) -> None:
        self.print_usage(sys.stderr)
        raise CliError("USAGE_ERROR", message)


def build_parser() -> argparse.ArgumentParser:
    p = JsonArgumentParser(prog="asecli", description="Agent-native CLI for Amplify Shader Editor assets")
    p.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
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
    s.add_argument("--force-external", action="store_true", help="allow removal despite external source references")
    s.add_argument("--write", action="store_true")
    s.set_defaults(func=cmd_remove_node)

    s = sub.add_parser("graph-audit", help="find output-dead nodes and distinguish external property consumers")
    s.add_argument("file")
    s.set_defaults(func=cmd_graph_audit)

    s = sub.add_parser("validate", help="validate graph structure")
    s.add_argument("file")
    s.set_defaults(func=cmd_validate)

    s = sub.add_parser("fix-checksum", help="recompute //CHKSM")
    s.add_argument("file")
    s.add_argument("--write", action="store_true")
    s.set_defaults(func=cmd_fix_checksum)

    s = sub.add_parser("layout", help="auto-arrange node positions (tidy)")
    s.add_argument("file")
    s.add_argument("--gap-x", type=float, default=280.0)
    s.add_argument("--gap-y", type=float, default=120.0)
    s.add_argument("--write", action="store_true")
    s.set_defaults(func=cmd_layout)

    s = sub.add_parser("custom-gui", help="inspect or edit CustomEditor and MZGUI-compatible property metadata")
    s.add_argument("file")
    target = s.add_mutually_exclusive_group()
    target.add_argument("--node", help="PropertyNode id for GUI metadata operations")
    target.add_argument("--property", help="exact ShaderLab property name, for example _PaintColor")
    s.add_argument("--spec", help="JSON file for atomic ordering/group/tooltip/help/enable operations")
    editor = s.add_mutually_exclusive_group()
    editor.add_argument("--editor", help="namespace-qualified ShaderGUI class")
    editor.add_argument("--clear-editor", action="store_true")
    group = s.add_mutually_exclusive_group()
    group.add_argument("--group", help="set FoldoutMzgui group title")
    group.add_argument("--clear-group", action="store_true")
    tooltip = s.add_mutually_exclusive_group()
    tooltip.add_argument("--tooltip", help="set TooltipMzgui text")
    tooltip.add_argument("--clear-tooltip", action="store_true")
    help_box = s.add_mutually_exclusive_group()
    help_box.add_argument("--help-box", help="set optional user-authored HelpBoxMzgui content")
    help_box.add_argument("--clear-help-box", action="store_true")
    enabled_if = s.add_mutually_exclusive_group()
    enabled_if.add_argument(
        "--enabled-if",
        metavar="PROPERTY",
        help="enable this control only when another float property matches",
    )
    enabled_if.add_argument("--clear-enabled-if", action="store_true")
    s.add_argument(
        "--enabled-if-operator",
        choices=ENABLE_IF_OPERATORS,
    )
    s.add_argument("--enabled-if-value", type=float)
    s.add_argument("--add-attribute", action="append", help="expert: add/replace an MZGUI-compatible metadata value")
    s.add_argument("--remove-attribute", action="append", help="expert: remove an MZGUI-compatible metadata type")
    s.add_argument("--write", action="store_true")
    s.set_defaults(func=cmd_custom_gui)

    s = sub.add_parser("gui-support", help="prefer native MZGUI, otherwise install the Editor fallback")
    s.add_argument("project", help="Unity/Tuanjie project root containing Assets and ProjectSettings")
    s.add_argument("--runtime-probe", action="store_true", help="confirm MZGUI.MZGUI by reflection in the connected Editor")
    s.add_argument("--mcp-url", default="http://127.0.0.1:8080/mcp")
    s.add_argument("--allow-remote-mcp", action="store_true")
    s.add_argument("--instance-token", dest="instance_token_argv", help=argparse.SUPPRESS)
    s.add_argument("--handoff-native", action="store_true", help="reversibly disable a known fallback for native MZGUI takeover")
    s.add_argument("--write", action="store_true", help="install the fallback into Assets/Editor only when MZGUI is absent")
    s.set_defaults(func=cmd_gui_support)

    s = sub.add_parser("install-skill", help="install the bundled ASECLI Agent Skill for Codex")
    s.add_argument(
        "--skill-root",
        help="Codex skills directory; defaults to $CODEX_HOME/skills or ~/.codex/skills",
    )
    s.set_defaults(func=cmd_install_skill)

    s = sub.add_parser("comment-group", help="inspect or create native ASE Comment frames")
    s.add_argument("file")
    s.add_argument("--fit", action="store_true", help="resize all existing frames using live ASE node bounds")
    s.add_argument(
        "--check-bounds",
        action="store_true",
        help="report members outside frames and unrelated Comment-frame overlaps",
    )
    s.add_argument("--editor-bounds", action="store_true", help="use live ASE bounds when creating a frame")
    s.add_argument("--nodes", help="comma-separated member node ids; Comment ids enable nesting")
    s.add_argument("--title", help="large functional or causal heading above the frame")
    s.add_argument("--note", help="small text in the Comment header; defaults to Comment")
    s.add_argument("--padding", type=float, help="frame padding in canvas units; defaults to 50")
    s.add_argument("--id", type=int, help="explicit Comment node id; defaults to the next free id")
    s.add_argument("--mcp-url", default="http://127.0.0.1:8080/mcp")
    s.add_argument(
        "--unity-instance",
        help="target Name@hash when multiple Unity/Tuanjie instances are connected",
    )
    s.add_argument("--allow-remote-mcp", action="store_true")
    s.add_argument("--instance-token", dest="instance_token_argv", help=argparse.SUPPRESS)
    s.add_argument("--write", action="store_true")
    s.set_defaults(func=cmd_comment_group)

    s = sub.add_parser("create", help="create new shader from a compiled template shell")
    s.add_argument("out")
    s.add_argument("--from", dest="from_template")
    s.add_argument("--name")
    s.add_argument("--graph-from", help="donor ASE file whose graph is injected")
    s.add_argument("--backend", choices=("text", "editor", "auto"), default="text")
    s.add_argument("--spec", help="strict EditorGraphSpec v2 JSON (editor/auto backend)")
    s.add_argument("--mcp-url", default="http://127.0.0.1:8080/mcp")
    s.add_argument("--allow-remote-mcp", action="store_true")
    s.add_argument("--instance-token", dest="instance_token_argv", help=argparse.SUPPRESS)
    s.add_argument("--force", action="store_true")
    s.set_defaults(func=cmd_create)

    s = sub.add_parser("recompile", help="trigger ASE regeneration inside running editor (MCP)")
    s.add_argument("file")
    s.add_argument("--mcp-url", default="http://127.0.0.1:8080/mcp")
    s.add_argument("--allow-remote-mcp", action="store_true")
    s.add_argument("--instance-token", dest="instance_token_argv", help=argparse.SUPPRESS)
    s.set_defaults(func=cmd_recompile)
    return p


def app(argv: list[str] | None = None) -> int:
    parser = build_parser()
    try:
        args = parser.parse_args(argv)
        data = args.func(args)
    except CliError as e:
        message = str(e)
        token = os.environ.get("ASECLI_MCP_INSTANCE_TOKEN")
        if token:
            message = message.replace(token, "<redacted>")
        payload = {"ok": False, "error": {"code": e.code, "message": message}}
        if e.data is not None:
            payload["data"] = e.data
        json.dump(payload, sys.stdout, ensure_ascii=False)
        sys.stdout.write("\n")
        return EXIT_BRIDGE if e.code == "BRIDGE_ERROR" else EXIT_ERROR
    except Exception as e:  # noqa: BLE001
        message = f"{type(e).__name__}: {e}"
        token = os.environ.get("ASECLI_MCP_INSTANCE_TOKEN")
        if token:
            message = message.replace(token, "<redacted>")
        json.dump({"ok": False, "error": {"code": "INTERNAL", "message": message}}, sys.stdout, ensure_ascii=False)
        sys.stdout.write("\n")
        return EXIT_ERROR
    json.dump({"ok": True, "data": data}, sys.stdout, ensure_ascii=False)
    sys.stdout.write("\n")
    return EXIT_OK


if __name__ == "__main__":
    raise SystemExit(app())
