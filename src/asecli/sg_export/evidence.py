"""Report evidence for template Passes and non-portable Inspector behavior."""

from __future__ import annotations

import re
import hashlib
import json

from .alpha_modulate import _strip_comments
from .model import MASTER_TYPE, URP_UNLIT_GUID, URP_UNLIT_PASSES, diagnostic


def record_custom_functions(nodes, report):
    manifest = []
    for node in nodes:
        if node.target_type != "custom-function" or node.function is None:
            continue
        canonical = json.dumps(node.function, ensure_ascii=False, sort_keys=True,
                               separators=(",", ":")).encode("utf-8")
        manifest.append({
            "source_node_id": node.source_id, "target_node_id": node.target_id,
            "function_sha256": hashlib.sha256(canonical).hexdigest(),
            "precision": node.settings.get("precision", "Inherit"),
            "mapping": "preserved_custom_function_payload",
        })
    report["custom_function_manifest"] = manifest


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
            report["presentation_warnings"].append({
                "source": {"property": name}, "code": "INSPECTOR_METADATA_NOT_MIGRATED",
                "details": present, "impact": "Property data is preserved; ASE Inspector UI behavior is not migrated",
                "classification": "presentation_only",
                "source_attributes": match.group("attrs").strip(),
                "material_side_effects": "none",
            })
    graph_gui = {node.raw_fields[9] for node in ase.graph.nodes
                         if node.type_name == MASTER_TYPE and len(node.raw_fields) > 9
                         and node.raw_fields[6] == "True"
                         and node.raw_fields[9] not in {"", "UnityEditor.ShaderGraphUnlitGUI"}}
    # Compiled ShaderLab may disagree with the ASE graph. Neither declaration
    # can be ignored when an unknown GUI can alter keywords/material state.
    shaderlab = ase.prefix.rsplit("/*ASEBEGIN", 1)[0]
    compiled_gui = set(re.findall(r'\bCustomEditor\s+"([^"]+)"', _strip_comments(shaderlab) or ""))
    custom_gui = (graph_gui | compiled_gui) - {"", "UnityEditor.ShaderGraphUnlitGUI"}
    known_presentation = sorted(custom_gui & {"MZGUI.MZGUI"})
    unknown_gui = sorted(custom_gui - {"MZGUI.MZGUI"})
    if known_presentation:
        report["presentation_warnings"].append({
            "source": {"file": str(report["source"]["path"])},
            "code": "CUSTOM_INSPECTOR_PRESENTATION_NOT_MIGRATED",
            "details": known_presentation,
            "classification": "presentation_only",
            "material_side_effects": "none",
            "impact": "MZGUI Inspector styling is not migrated; Shader properties and runtime graph semantics are unchanged",
        })
    if unknown_gui:
        report["degradations"].append({
            "source": {"file": str(report["source"]["path"])}, "code": "CUSTOM_INSPECTOR_NOT_MIGRATED",
            "details": unknown_gui,
            "classification": "custom_shader_gui",
            "material_side_effects": "unproven",
            "impact": "ShaderGUI behavior has no equivalent in the creation specification",
        })
    if report["degradations"]:
        report["equivalence"] = {"status": "degraded", "reason": "Inspector behavior and possible material side effects were not proved equivalent"}


def record_port(report, source_id, source_port, source_end, target_id, target_port, target_end):
    for row in report["mappings"]:
        if source_id in row["source_nodes"]:
            row["ports"].append({"source": [source_id, source_port], "target": list(source_end)})
        if target_id in row["source_nodes"]:
            row["ports"].append({"source": [target_id, target_port], "target": list(target_end)})
