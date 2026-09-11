"""Expose consumer-owned JSON Schemas through the CLI."""

from __future__ import annotations

from ..bridge import SpecError, load_editor_graph_spec_with_sha256
from ..contracts import load_editor_graph_schema
from .commands import CliError


def configure_contract_parser(sub) -> None:
    parser = sub.add_parser("contract", help="print an authoritative ASECLI consumer schema")
    parser.add_argument("contract_name", choices=("editor-graph",))
    parser.add_argument("--version", type=int, choices=(3,), default=3)
    parser.add_argument("--spec", help="validate a spec against this contract without Editor access")
    parser.set_defaults(func=cmd_contract)


def cmd_contract(args) -> dict:
    result = {
        "contract": f"EditorGraphSpec.v{args.version}",
        "schema": load_editor_graph_schema(args.version),
    }
    if getattr(args, "spec", None):
        try:
            spec, digest = load_editor_graph_spec_with_sha256(args.spec)
        except FileNotFoundError as exc:
            raise CliError("NOT_FOUND", str(exc)) from exc
        except SpecError as exc:
            raise CliError("VALIDATION_ERROR", str(exc)) from exc
        if spec.version != args.version:
            raise CliError("SCHEMA_VERSION_MISMATCH", f"expected EditorGraphSpec v{args.version}")
        result.update(validated=True, spec_sha256=digest)
    return result
