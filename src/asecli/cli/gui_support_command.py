"""CLI composition for the built-in ASECLI Unity material GUI."""

from __future__ import annotations

import os

from ..bridge import (
    EDITOR_ERRORS,
    handoff_gui_support,
    install_gui_support,
    probe_native_mzgui_via_mcp,
)
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
                backend=args.editor_backend,
                codely_port=args.codely_port,
            )
        operation = handoff_gui_support if args.handoff_native else install_gui_support
        return operation(args.project, write=args.write, runtime_probe=runtime_probe)
    except FileNotFoundError as exc:
        raise CliError("NOT_FOUND", str(exc)) from exc
    except EDITOR_ERRORS as exc:
        raise CliError("BRIDGE_ERROR", str(exc), exc.data) from exc
    except (FileExistsError, ValueError, RuntimeError, OSError) as exc:
        raise CliError("GUI_SUPPORT_ERROR", str(exc)) from exc
