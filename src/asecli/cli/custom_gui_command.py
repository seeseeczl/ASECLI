"""CLI composition for ASE CustomEditor and property metadata."""

from __future__ import annotations

import json
from pathlib import Path

from ..checks import fix_checksum, validate_file
from ..core import (
    ASECLI_GUI_EDITOR,
    MZGUI_EDITOR,
    SUPPORTED_GUI_EDITORS,
    apply_material_gui_spec,
    enable_if_attribute,
    graph_custom_editor,
    inspect_custom_gui,
    remove_property_metadata_attribute,
    resolve_property_node,
    semantic_attribute,
    set_custom_editor,
    set_property_metadata_attribute,
    sync_compiled_property_metadata,
)
from .commands import CliError, _commit_text, _load


def cmd_custom_gui(args) -> dict:
    """Inspect or safely mutate ASE CustomEditor and ASECLI property metadata."""
    if args.enabled_if is not None and args.enabled_if_value is None:
        raise CliError("USAGE_ERROR", "--enabled-if requires --enabled-if-value")
    if args.enabled_if is None and args.enabled_if_value is not None:
        raise CliError("USAGE_ERROR", "--enabled-if-value requires --enabled-if")
    if args.enabled_if is None and args.enabled_if_operator is not None:
        raise CliError("USAGE_ERROR", "--enabled-if-operator requires --enabled-if")
    f = _load(args.file)
    changes = []
    node_actions = any(
        (
            args.group is not None,
            args.clear_group,
            args.tooltip is not None,
            args.clear_tooltip,
            args.help_box is not None,
            args.clear_help_box,
            args.enabled_if is not None,
            args.clear_enabled_if,
            bool(args.add_attribute),
            bool(args.remove_attribute),
        )
    )
    single_mutation = node_actions or args.editor is not None or args.clear_editor
    if args.spec and single_mutation:
        raise CliError("USAGE_ERROR", "--spec cannot be combined with individual custom GUI mutation options")
    if args.spec and (args.node is not None or args.property is not None):
        raise CliError("USAGE_ERROR", "--spec cannot be combined with --node or --property")
    if node_actions and args.node is None and args.property is None:
        raise CliError("USAGE_ERROR", "--node or --property is required for ASECLI property metadata operations")

    try:
        initial_presentation = inspect_custom_gui(f)["property_presentation"]
        if args.spec:
            changes.extend(apply_material_gui_spec(f, _load_spec(args.spec)))
        else:
            if args.editor is not None:
                changes.append(set_custom_editor(f, args.editor))
            elif args.clear_editor:
                changes.append(set_custom_editor(f, None))

            target = None
            if args.node is not None or args.property is not None:
                target = resolve_property_node(
                    f.graph, node_id=args.node, property_name=args.property
                ).node_id

            additions: list[str] = []
            if args.group is not None:
                additions.append(semantic_attribute("FoldoutMzgui", args.group))
            if args.tooltip is not None:
                additions.append(semantic_attribute("TooltipMzgui", args.tooltip))
            if args.help_box is not None:
                additions.append(semantic_attribute("HelpBoxMzgui", args.help_box))
            if args.enabled_if is not None:
                additions.append(
                    enable_if_attribute(
                        args.enabled_if,
                        args.enabled_if_operator or "Equal",
                        args.enabled_if_value,
                    )
                )
            additions.extend(args.add_attribute or [])

            if additions and graph_custom_editor(f.graph) not in SUPPORTED_GUI_EDITORS:
                supported = ", ".join(sorted(SUPPORTED_GUI_EDITORS))
                raise ValueError(
                    "MZGUI-compatible property metadata requires a selected material GUI; "
                    f"pass --editor with one of: {supported}"
                )

            removals = (
                [(args.clear_group, "FoldoutMzgui"), (args.clear_tooltip, "TooltipMzgui"),
                 (args.clear_help_box, "HelpBoxMzgui"),
                 (args.clear_enabled_if, "EnableIfMzgui")]
            )
            for enabled, type_name in removals:
                if enabled:
                    changes.append(remove_property_metadata_attribute(f.graph, target, type_name))
            for type_name in args.remove_attribute or []:
                changes.append(remove_property_metadata_attribute(f.graph, target, type_name))
            for raw in additions:
                changes.append(set_property_metadata_attribute(f.graph, target, raw))

        if changes and graph_custom_editor(f.graph) == ASECLI_GUI_EDITOR:
            changes.insert(0, set_custom_editor(f, MZGUI_EDITOR))
        if changes:
            changes.extend(sync_compiled_property_metadata(f))
        state = inspect_custom_gui(f)
    except KeyError as exc:
        raise CliError("NOT_FOUND", str(exc))
    except ValueError as exc:
        raise CliError("CUSTOM_GUI_ERROR", str(exc))

    if not changes:
        if args.write:
            raise CliError("USAGE_ERROR", "--write requires a custom GUI mutation option")
        return {"file": args.file, "action": "inspect", "state": state, "written": False}

    contract_applies = initial_presentation["claimed"] or state["property_presentation"]["claimed"]
    if args.write and contract_applies and not state["property_presentation"]["valid"]:
        raise CliError(
            "PROPERTY_PRESENTATION_ERROR",
            "ASECLI-managed property presentation contract failed: "
            + ", ".join(state["property_presentation"]["violations"]),
            {"property_presentation": state["property_presentation"]},
        )

    issues = validate_file(f)
    errors = [issue for issue in issues if issue["severity"] == "error"]
    if errors:
        raise CliError(
            "VALIDATION_ERROR",
            f"mutation would leave {len(errors)} structural error(s)",
            {"issues": issues, "error_count": len(errors)},
        )
    output = fix_checksum(f.serialize())
    if args.write:
        _commit_text(args.file, output, f.source_digest)
    return {
        "file": args.file,
        "action": "mutate",
        "changes": changes,
        "state": state,
        "requires_recompile": bool(changes),
        "written": bool(args.write),
        "path": args.file if args.write else None,
        "preview_bytes": len(output),
        "checksum_recomputed": True,
    }


def _load_spec(path: str) -> dict:
    try:
        text = Path(path).read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise KeyError(f"spec file not found: {path}") from exc
    except UnicodeDecodeError as exc:
        raise ValueError(f"material GUI spec is not valid UTF-8: {path}") from exc
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid material GUI spec JSON at line {exc.lineno}, column {exc.colno}") from exc
