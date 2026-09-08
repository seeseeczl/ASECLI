"""Safe shader creation and semantic Shader-name mutation."""

from __future__ import annotations

import os
from pathlib import Path
import re

from ..bridge import (
    MZGUI_EDITOR,
    McpError,
    SpecError,
    create_shader_via_mcp,
    install_gui_support,
    load_editor_graph_spec,
    route_create_backend,
)
from ..checks import ChecksumFormatError, fix_checksum, validate_file
from ..core import (
    AseFile,
    apply_material_gui_spec,
    main_master_node,
    require_property_presentation,
    sync_compiled_property_metadata,
)
from .commands import CliError, _commit_text, _load
from .gui_provider import select_editor_provider
from .io import UnsafeWritePathError, file_digest


_SHADER_DECLARATION = re.compile(r'(?m)^(?P<indent>[ \t]*)Shader[ \t]+"(?P<name>[^"\r\n]+)"')
_TEMPLATE_NAME_FIELD = {
    "AmplifyShaderEditor.TemplateMultiPassMasterNode": 12,
    "AmplifyShaderEditor.TemplateMasterNode": 12,
}


def cmd_create(args) -> dict:
    spec = None
    if args.spec:
        try:
            spec = load_editor_graph_spec(args.spec)
        except FileNotFoundError as exc:
            raise CliError("NOT_FOUND", str(exc)) from exc
        except SpecError as exc:
            raise CliError("USAGE_ERROR", str(exc)) from exc
    try:
        backend = route_create_backend(args.backend, spec)
    except SpecError as exc:
        raise CliError("USAGE_ERROR", str(exc)) from exc
    if backend == "editor":
        return _cmd_create_editor(args, spec)
    return _cmd_create_text(args, spec)


def _cmd_create_text(args, spec) -> dict:
    if spec is not None:
        raise CliError("USAGE_ERROR", "--spec requires --backend editor or auto")
    if not args.from_template:
        raise CliError("USAGE_ERROR", "--from is required for the text create backend")
    f = _load(args.from_template)
    if args.graph_from:
        donor = _load(args.graph_from)
        f.replace_graph(donor.graph)
    if args.name:
        _set_shader_name(f, args.name)
    try:
        text = fix_checksum(f.serialize())
    except ChecksumFormatError as exc:
        raise CliError("CHECKSUM_FORMAT_ERROR", str(exc)) from exc
    try:
        created = AseFile.from_text(text)
        errors = [issue for issue in validate_file(created) if issue["severity"] == "error"]
    except ValueError as exc:
        raise CliError("VALIDATION_ERROR", f"created shader is not parseable: {exc}") from exc
    if errors:
        raise CliError(
            "VALIDATION_ERROR",
            f"created shader contains {len(errors)} structural error(s)",
            {"issues": errors, "error_count": len(errors)},
        )
    try:
        presentation = require_property_presentation(created)
    except ValueError as exc:
        raise CliError("PROPERTY_PRESENTATION_ERROR", str(exc)) from exc
    try:
        output_digest = file_digest(args.out)
    except FileNotFoundError:
        output_digest = None
    except UnsafeWritePathError as exc:
        raise CliError("UNSAFE_PATH", str(exc)) from exc
    if output_digest is not None and not args.force:
        raise CliError("USAGE_ERROR", f"{args.out} exists (use --force)")
    _commit_text(args.out, text, output_digest)
    return {
        "created": args.out,
        "name": args.name,
        "graph_from": args.graph_from,
        "backend": "text",
        "property_presentation": presentation,
    }


def _cmd_create_editor(args, spec) -> dict:
    if spec is None:
        raise CliError("USAGE_ERROR", "--spec is required for the editor create backend")
    if spec.version not in {2, 3}:
        raise CliError(
            "USAGE_ERROR",
            "CLI Editor creation requires EditorGraphSpec v2 or v3 with Chinese inspector_name and help for every property",
        )
    if args.from_template or args.graph_from or args.name:
        raise CliError("USAGE_ERROR", "--from, --graph-from and --name are text-backend options")
    if args.force:
        raise CliError("USAGE_ERROR", "editor create only supports absent targets; --force is not allowed")
    if args.instance_token_argv is not None:
        raise CliError("USAGE_ERROR", "do not pass MCP tokens via argv; use ASECLI_MCP_INSTANCE_TOKEN")
    try:
        selected_editor, gui_support = select_editor_provider(args.out)
    except (FileNotFoundError, ValueError, RuntimeError, OSError) as exc:
        raise CliError("GUI_SUPPORT_ERROR", str(exc)) from exc
    try:
        result = create_shader_via_mcp(
            args.out,
            spec,
            mcp_url=args.mcp_url,
            instance_token=os.environ.get("ASECLI_MCP_INSTANCE_TOKEN"),
            allow_remote_mcp=args.allow_remote_mcp,
        )
    except McpError as exc:
        raise CliError("BRIDGE_ERROR", str(exc), exc.data) from exc
    except FileExistsError as exc:
        raise CliError("USAGE_ERROR", str(exc)) from exc
    except FileNotFoundError as exc:
        raise CliError("NOT_FOUND", str(exc)) from exc
    except ValueError as exc:
        raise CliError("USAGE_ERROR", str(exc)) from exc

    try:
        created = AseFile.from_path(args.out)
        errors = [issue for issue in validate_file(created) if issue["severity"] == "error"]
    except (OSError, UnicodeError, ValueError) as exc:
        raise CliError(
            "BRIDGE_ERROR",
            f"Editor-created shader is not parseable and was preserved for diagnosis: {exc}",
            _preserved_editor_asset_details(args.out, result),
        ) from exc
    if errors:
        raise CliError(
            "BRIDGE_ERROR",
            f"Editor-created shader contains {len(errors)} structural error(s) and was preserved for diagnosis",
            {
                "issues": errors,
                "error_count": len(errors),
                **_preserved_editor_asset_details(args.out, result),
            },
        )
    try:
        output, presentation = _finalize_editor_property_presentation(
            created, spec, editor=selected_editor
        )
        _commit_text(args.out, output, created.source_digest)
        result["shader_sha256"] = file_digest(args.out)
    except (OSError, UnicodeError, ValueError) as exc:
        raise CliError(
            "BRIDGE_ERROR",
            f"Editor-created shader failed property-presentation finalization and was preserved for diagnosis: {exc}",
            _preserved_editor_asset_details(args.out, result),
        ) from exc
    return {
        "created": args.out,
        "backend": "editor",
        "gui_support": gui_support,
        "property_presentation": presentation,
        **result,
    }


def _finalize_editor_property_presentation(
    created: AseFile, spec, *, editor: str = MZGUI_EDITOR
) -> tuple[str, dict]:
    """Apply the same v2 presentation contract after ASE commits an Editor graph."""
    presentation_spec = {
        "editor": editor,
        "properties": [
            {
                "name": node.property_name,
                "display_name": node.inspector_name,
                "tooltip": node.tooltip,
                "help": node.help,
                "enabled_if": node.enabled_if,
            }
            for node in spec.nodes
            if node.property_name is not None
        ],
    }
    apply_material_gui_spec(created, presentation_spec)
    sync_compiled_property_metadata(created)
    from asecli.core.compiled_metadata import hide_known_template_compiled_only_properties

    hide_known_template_compiled_only_properties(created, spec.template.guid)
    presentation = require_property_presentation(created)
    return fix_checksum(created.serialize()), presentation

def _preserved_editor_asset_details(path: str, result: dict) -> dict:
    """Describe a post-commit failure without deleting an identity that may have changed."""
    return {
        "preserved_path": str(Path(path).resolve()),
        "cleanup": "skipped_untrusted_post_commit_asset",
        "transaction_nonce": result.get("transaction_nonce"),
        "shader_sha256": result.get("shader_sha256"),
        "meta_sha256": result.get("meta_sha256"),
    }


def _set_shader_name(ase_file: AseFile, name: str) -> None:
    if not name.strip() or len(name) > 255:
        raise CliError("USAGE_ERROR", "shader name must be 1-255 non-whitespace characters")
    if any(ord(char) < 32 for char in name) or any(char in name for char in ('"', "'", ";", "\\")):
        raise CliError("USAGE_ERROR", "shader name contains a forbidden quote, separator, escape, or control character")
    matches = list(_SHADER_DECLARATION.finditer(ase_file.prefix))
    if len(matches) != 1:
        raise CliError("USAGE_ERROR", f"template must contain exactly one Shader declaration, found {len(matches)}")
    declaration = matches[0]
    ase_file.prefix = (
        ase_file.prefix[: declaration.start("name")]
        + name
        + ase_file.prefix[declaration.end("name") :]
    )

    try:
        master = main_master_node(ase_file.graph)
    except ValueError as exc:
        if any("MasterNode" in node.type_name for node in ase_file.graph.nodes):
            raise CliError("USAGE_ERROR", f"cannot resolve graph Master name field: {exc}") from exc
        return
    index = _TEMPLATE_NAME_FIELD.get(master.type_name)
    if index is None:
        old_name = declaration.group("name")
        candidates = [i for i, value in enumerate(master.raw_fields) if value == old_name]
        if len(candidates) != 1:
            raise CliError(
                "USAGE_ERROR",
                f"unsupported Master name layout for {master.type_name}: found {len(candidates)} candidate fields",
            )
        index = candidates[0]
    if index >= len(master.raw_fields):
        raise CliError("USAGE_ERROR", f"Master node {master.node_id} has no shader-name field {index}")
    master.raw_fields[index] = name
    ase_file.graph.replace_node(master)
