"""CLI composition for native ASE Comment-frame grouping."""

from __future__ import annotations

import os

from ..bridge import McpError, measure_node_bounds_via_mcp
from ..checks import fix_checksum, validate_file
from ..core import (
    comment_containment_issues,
    create_comment_group,
    inspect_comment_groups,
    refit_comment_groups,
)
from .commands import CliError, _commit_text, _load


def cmd_comment_group(args) -> dict:
    f = _load(args.file)
    if args.fit:
        if args.nodes is not None or args.title is not None or args.note is not None or args.id is not None:
            raise CliError("USAGE_ERROR", "--fit cannot be combined with Comment creation options")
        bounds = _editor_bounds(args)
        try:
            before = comment_containment_issues(f.graph, bounds)
            changes = refit_comment_groups(
                f.graph,
                bounds,
                padding=50.0 if args.padding is None else args.padding,
            )
            after = comment_containment_issues(f.graph, bounds)
        except KeyError as exc:
            raise CliError("NOT_FOUND", str(exc))
        except ValueError as exc:
            raise CliError("COMMENT_GROUP_ERROR", str(exc))
        overlaps = [issue for issue in after if issue["code"] == "COMMENT_GROUP_OVERLAP"]
        if args.write and overlaps:
            raise CliError(
                "COMMENT_GROUP_ERROR",
                f"fit would leave {len(overlaps)} unrelated Comment group overlap(s); move groups apart first",
                {"issues": overlaps, "error_count": len(overlaps)},
            )
        output = _validated_output(f)
        if args.write:
            _commit_text(args.file, output, f.source_digest)
        return {
            "file": args.file,
            "action": "fit",
            "measurement": "live_ase_true_position",
            "padding": 50.0 if args.padding is None else args.padding,
            "changes": changes,
            "changed_count": len(changes),
            "before_issues": before,
            "after_issues": after,
            "written": bool(args.write),
            "path": args.file if args.write else None,
            "preview_bytes": len(output),
            "checksum_recomputed": True,
            "requires_editor_reload": True,
        }

    if args.nodes is None:
        if any((args.title is not None, args.note is not None, args.padding is not None,
                args.id is not None, args.write, args.editor_bounds)):
            raise CliError("USAGE_ERROR", "--nodes and --title are required to create a comment group")
        try:
            groups = inspect_comment_groups(f.graph)
        except ValueError as exc:
            raise CliError("COMMENT_GROUP_ERROR", str(exc))
        data = {"file": args.file, "action": "inspect", "groups": groups, "written": False}
        if args.check_bounds:
            bounds = _editor_bounds(args)
            try:
                data["measurement"] = "live_ase_true_position"
                data["containment_issues"] = comment_containment_issues(f.graph, bounds)
            except ValueError as exc:
                raise CliError("COMMENT_GROUP_ERROR", str(exc))
        return data
    if args.title is None:
        raise CliError("USAGE_ERROR", "--title is required with --nodes")
    if args.check_bounds:
        raise CliError("USAGE_ERROR", "--check-bounds cannot be combined with Comment creation")
    member_ids = [item.strip() for item in args.nodes.split(",")]
    if any(not item for item in member_ids):
        raise CliError("USAGE_ERROR", "--nodes must be a comma-separated list of node ids")

    bounds = _editor_bounds(args) if args.editor_bounds else None
    try:
        group = create_comment_group(
            f.graph,
            member_ids,
            args.title,
            note="Comment" if args.note is None else args.note,
            padding=50.0 if args.padding is None else args.padding,
            node_id=args.id,
            node_bounds=bounds,
        )
    except KeyError as exc:
        raise CliError("NOT_FOUND", str(exc))
    except ValueError as exc:
        raise CliError("COMMENT_GROUP_ERROR", str(exc))

    output = _validated_output(f)
    if args.write:
        _commit_text(args.file, output, f.source_digest)
    return {
        "file": args.file,
        "action": "create",
        "group": group,
        "written": bool(args.write),
        "path": args.file if args.write else None,
        "preview_bytes": len(output),
        "checksum_recomputed": True,
        "requires_editor_reload": True,
        "measurement": "live_ase_true_position" if bounds is not None else "offline_estimate",
    }


def _editor_bounds(args) -> dict[str, tuple[float, float, float, float]]:
    if args.instance_token_argv is not None:
        raise CliError("USAGE_ERROR", "do not pass MCP tokens via argv; use ASECLI_MCP_INSTANCE_TOKEN")
    try:
        return measure_node_bounds_via_mcp(
            args.file,
            mcp_url=args.mcp_url,
            instance_token=os.environ.get("ASECLI_MCP_INSTANCE_TOKEN"),
            allow_remote_mcp=args.allow_remote_mcp,
        )
    except McpError as exc:
        raise CliError("BRIDGE_ERROR", str(exc))
    except FileNotFoundError as exc:
        raise CliError("NOT_FOUND", str(exc))
    except ValueError as exc:
        raise CliError("USAGE_ERROR", str(exc))


def _validated_output(f) -> str:
    issues = validate_file(f)
    errors = [issue for issue in issues if issue["severity"] == "error"]
    if errors:
        raise CliError(
            "VALIDATION_ERROR",
            f"mutation would leave {len(errors)} structural error(s)",
            {"issues": issues, "error_count": len(errors)},
        )
    return fix_checksum(f.serialize())
