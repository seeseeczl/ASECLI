"""Stable machine-readable CLI response contract."""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any

from .commands import CliError


CONTRACT_VERSION = 1
ERROR_CODES = frozenset(
    {
        "BRIDGE_ERROR",
        "CHECKSUM_FORMAT_ERROR",
        "COMMENT_GROUP_ERROR",
        "CUSTOM_GUI_ERROR",
        "EXTERNAL_REFERENCE",
        "GRAPH_REVIEW_ERROR",
        "GUI_SUPPORT_ERROR",
        "INTERNAL",
        "LAYOUT_ERROR",
        "NOT_FOUND",
        "PARSE_ERROR",
        "PROPERTY_PRESENTATION_ERROR",
        "SCHEMA_UNAVAILABLE",
        "SCHEMA_VERSION_MISMATCH",
        "SEMANTIC_MISMATCH",
        "SG_EXPORT_BLOCKED",
        "SKILL_INSTALL_CONFLICT",
        "SKILL_INSTALL_ERROR",
        "UNSAFE_PATH",
        "USAGE_ERROR",
        "VALIDATION_ERROR",
        "WRITE_CONFLICT",
        "WRITE_ERROR",
        "WRITE_PARTIAL",
    }
)


class JsonArgumentParser(argparse.ArgumentParser):
    """Keep argparse diagnostics on stderr while routing failures through JSON."""

    def error(self, message: str) -> None:
        self.print_usage(sys.stderr)
        raise CliError("USAGE_ERROR", message)


class JsonVersionRequested(Exception):
    """Route argparse's version action through the JSON response writer."""


class JsonVersionAction(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None) -> None:
        del parser, namespace, values, option_string
        raise JsonVersionRequested


def envelope(*, cli_version: str, command: str | None, data: Any = None, error: dict | None = None) -> dict:
    payload = {
        "contract_version": CONTRACT_VERSION,
        "cli_version": cli_version,
        "command": command,
        "ok": error is None,
    }
    payload["data" if error is None else "error"] = data if error is None else error
    return payload


def emit_json(payload: dict, *, cli_version: str, command: str | None) -> bool:
    """Serialize before writing so encoding/serialization cannot leave a partial prefix."""
    serialized = True
    try:
        output = json.dumps(payload, ensure_ascii=True, allow_nan=False, separators=(",", ":")) + "\n"
    except (TypeError, ValueError):
        serialized = False
        fallback = envelope(
            cli_version=cli_version,
            command=command,
            error={"code": "INTERNAL", "message": "response is not JSON serializable"},
        )
        output = json.dumps(fallback, ensure_ascii=True, allow_nan=False, separators=(",", ":")) + "\n"

    encoded = output.encode("ascii")
    try:
        stream = getattr(sys.stdout, "buffer", None)
        if stream is None:
            sys.stdout.write(output)
            sys.stdout.flush()
        else:
            stream.write(encoded)
            stream.flush()
    except (OSError, UnicodeError):
        try:
            sys.stderr.write("asecli: unable to write JSON response\n")
            sys.stderr.flush()
        except (OSError, UnicodeError):
            pass
        return False
    return serialized


def command_hint(parser: argparse.ArgumentParser, argv: list[str]) -> str | None:
    subparsers = next(
        (action for action in parser._actions if isinstance(action, argparse._SubParsersAction)),
        None,
    )
    if subparsers is None or not argv:
        return None
    return argv[0] if argv[0] in subparsers.choices else None


def redact(message: str) -> str:
    token = os.environ.get("ASECLI_MCP_INSTANCE_TOKEN")
    return message.replace(token, "<redacted>") if token else message
