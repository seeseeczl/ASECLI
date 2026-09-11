"""Report evidence for template Passes and non-portable Inspector behavior."""

from __future__ import annotations

import re

from .model import MASTER_TYPE, URP_UNLIT_GUID, URP_UNLIT_PASSES, diagnostic


def validate_template_passes(ase, master, diagnostics, report):
    masters = [node for node in ase.graph.nodes if node.type_name == MASTER_TYPE]
    passes = {node.raw_fields[15] for node in masters if len(node.raw_fields) > 15}
    bad_guids = [node.node_id for node in masters
                 if len(node.raw_fields) <= 13 or node.raw_fields[13] != URP_UNLIT_GUID]
    master_ids = {node.node_id for node in masters}
    connected_non_active = sorted({wire.in_node for wire in ase.graph.wires
                                   if wire.in_node in master_ids
                                   and (master is None or wire.in_node != master.node_id)})
    legacy_single = ase.graph.version == "19109" and passes == {"Forward"} and len(masters) == 1
    exact_standard_set = passes == URP_UNLIT_PASSES and len(masters) == len(URP_UNLIT_PASSES)
    if (not exact_standard_set and not legacy_single) or bad_guids or connected_non_active:
        diagnostics.append(diagnostic(None, "MULTIPASS_UNSUPPORTED", {
            "passes": sorted(passes), "unexpected_template_nodes": bad_guids,
            "connected_non_active_passes": connected_non_active,
        }, "ASE Pass behavior cannot be represented by the selected SG Target"))
        return
    report["mappings"].append({
        "source_nodes": [node.node_id for node in masters], "target_nodes": ["URP.UnlitTarget"],
        "kind": "certified_template_pass_set", "passes": sorted(passes), "ports": [],
    })


def inspector_degradations(ase, properties, report):
    names = {row["name"] for row in properties}
    attributes = ("FoldoutMzgui", "EnableIfMzgui", "TooltipMzgui", "HelpBoxMzgui",
                  "ASECLIFoldout", "ASECLIEnableIf", "ASECLITooltip", "ASECLIHelpBox")
    for name in sorted(names):
        match = re.search(rf"(?m)^\s*(?P<attrs>(?:\[[^\]\r\n]*\]\s*)*){re.escape(name)}\s*\(", ase.prefix)
        present = [kind for kind in attributes if match and f"[{kind}" in match.group("attrs")]
        if present:
            report["degradations"].append({
                "source": {"property": name}, "code": "INSPECTOR_METADATA_NOT_MIGRATED",
                "details": present, "impact": "Property data is preserved; ASE Inspector UI behavior is not migrated",
            })
    custom_gui = any(node.type_name == MASTER_TYPE and len(node.raw_fields) > 9
                     and node.raw_fields[6] == "True"
                     and node.raw_fields[9] not in {"", "UnityEditor.ShaderGraphUnlitGUI"}
                     for node in ase.graph.nodes)
    if custom_gui:
        report["degradations"].append({
            "source": {"file": str(report["source"]["path"])}, "code": "CUSTOM_INSPECTOR_NOT_MIGRATED",
            "impact": "ShaderGUI behavior has no equivalent in the creation specification",
        })
    if report["degradations"]:
        report["equivalence"] = {"status": "degraded", "reason": "Inspector-only semantics were not migrated"}


def record_port(report, source_id, source_port, source_end, target_id, target_port, target_end):
    for row in report["mappings"]:
        if source_id in row["source_nodes"]:
            row["ports"].append({"source": [source_id, source_port], "target": list(source_end)})
        if target_id in row["source_nodes"]:
            row["ports"].append({"source": [target_id, target_port], "target": list(target_end)})
