"""CLI composition for liveness audit and externally safe node removal."""

from __future__ import annotations

from ..checks import external_references_for_node, usage_audit
from ..core import remove_node
from .commands import CliError, _load, _save


def cmd_remove_node(args) -> dict:
    f = _load(args.file)
    target = f.graph.node_by_id(args.node)
    if target is None:
        raise CliError("NOT_FOUND", f"node {args.node} not found")
    if not args.force_external:
        try:
            references = external_references_for_node(args.file, target)
        except ValueError as exc:
            raise CliError("USAGE_ERROR", str(exc))
        if references:
            raise CliError(
                "EXTERNAL_REFERENCE",
                f"node {args.node} property {target.raw_fields[7]} is referenced outside the ASE graph",
                {"node_id": args.node, "property_name": target.raw_fields[7], "references": references},
            )
    try:
        wires = remove_node(f.graph, args.node)
    except KeyError as exc:
        raise CliError("NOT_FOUND", str(exc))
    except ValueError as exc:
        raise CliError("VALIDATION_ERROR", str(exc))
    saved = _save(f, args.file, args.write)
    return {"removed_node": args.node, "removed_wires": wires, **saved}


def cmd_graph_audit(args) -> dict:
    f = _load(args.file)
    try:
        audit = usage_audit(args.file, f.graph)
    except ValueError as exc:
        raise CliError("USAGE_ERROR", str(exc))
    return {"file": args.file, **audit}
