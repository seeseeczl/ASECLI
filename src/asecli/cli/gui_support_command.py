"""CLI composition for the built-in ASECLI Unity material GUI."""

from __future__ import annotations

from ..bridge import install_gui_support
from .commands import CliError


def cmd_gui_support(args) -> dict:
    try:
        return install_gui_support(args.project, write=args.write)
    except FileNotFoundError as exc:
        raise CliError("NOT_FOUND", str(exc)) from exc
    except (FileExistsError, ValueError, RuntimeError, OSError) as exc:
        raise CliError("GUI_SUPPORT_ERROR", str(exc)) from exc
