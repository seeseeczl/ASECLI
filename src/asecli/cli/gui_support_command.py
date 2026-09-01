"""CLI composition for the built-in Unity material GUI compatibility layer."""

from __future__ import annotations

import os

from ..bridge import McpError, install_gui_support, probe_native_mzgui_via_mcp
from .commands import CliError


def cmd_gui_support(args) -> dict:
    if args.instance_token_argv is not None:
        raise CliError("USAGE_ERROR", "do not pass MCP tokens via argv; use ASECLI_MCP_INSTANCE_TOKEN")
    try:
        runtime_probe = None
        if args.runtime_probe:
            runtime_probe = probe_native_mzgui_via_mcp(
                args.project,
                mcp_url=args.mcp_url,
                instance_token=os.environ.get("ASECLI_MCP_INSTANCE_TOKEN"),
                allow_remote_mcp=args.allow_remote_mcp,
            )
        return install_gui_support(args.project, write=args.write, runtime_probe=runtime_probe)
    except FileNotFoundError as exc:
        raise CliError("NOT_FOUND", str(exc)) from exc
    except (FileExistsError, ValueError, RuntimeError, OSError, McpError) as exc:
        raise CliError("GUI_SUPPORT_ERROR", str(exc)) from exc
