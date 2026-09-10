"""Build an unbound SGCLI candidate from certified ASE semantics."""

from __future__ import annotations

import hashlib
from pathlib import Path

from ..core.commentary import COMMENTARY_TYPE
from ..core.local_vars import GET_LOCAL_VAR_TYPE, REGISTER_LOCAL_VAR_TYPE, parse_get_local_var
from ..core.model import AseFile
from ..checks.validate import validate_file
from .model import (
    ExportError, MASTER_OUTPUTS, MASTER_TYPE, SUPPORTED_ASE_VERSIONS, URP_UNLIT_GUID,
    WIRE_TYPE, SemanticEdge, diagnostic, report_template, status,
)
from .nodes import convert_node
from .sources import compiled_properties, load_asset_map
from .evidence import inspector_degradations, validate_template_passes
from .reconciliation import (
    groups, reconcile_shaderlab_properties, unique_properties, verify_texture_dependencies,
)


def build_candidate(source_path, target_project, *, name=None, asset_map_path=None):
    source, target = Path(source_path).resolve(), Path(target_project).resolve()
    text = source.read_text(encoding="utf-8")
    ase = AseFile.from_text(text)
    report = report_template(source, target, ase.graph.version, text)
    report["source"]["sha256"] = hashlib.sha256(source.read_bytes()).hexdigest()
    diagnostics = report["diagnostics"]
    issues = validate_file(ase)
    structural_errors = [item for item in issues if item.get("severity") == "error"]
    report["source_validation"] = {
        "error_count": len(structural_errors),
        "warning_count": sum(item.get("severity") == "warning" for item in issues),
        "issues": issues,
    }
    for issue in structural_errors:
        diagnostics.append(diagnostic(
            issue.get("node_id"), issue.get("code", "SOURCE_STRUCTURE_INVALID"),
            issue.get("message", "ASE structural validation failed"),
            "Source graph structure is invalid; no conversion can be claimed",
        ))
    if ase.graph.version not in SUPPORTED_ASE_VERSIONS:
        diagnostics.append(diagnostic(None, "ASE_VERSION_UNSUPPORTED",
            f"ASE version {ase.graph.version} has no certified export decoder",
            "Node defaults and port records cannot be trusted"))
    incoming = {}
    for wire in ase.graph.wires:
        endpoint = (wire.in_node, int(wire.in_port))
        if endpoint in incoming:
            diagnostics.append(diagnostic(wire.in_node, "DUPLICATE_INPUT",
                f"input {wire.in_port} has multiple sources", "ASE computation is structurally ambiguous"))
        incoming[endpoint] = wire
    active = sorted({w.in_node for w in ase.graph.wires
                     if (ase.graph.node_by_id(w.in_node) and ase.graph.node_by_id(w.in_node).type_name == MASTER_TYPE)})
    if len(active) != 1:
        diagnostics.append(diagnostic(None, "MASTER_AMBIGUOUS", f"expected one connected Master, found {len(active)}",
                                      "Target and output blocks cannot be determined"))
    master = ase.graph.node_by_id(active[0]) if len(active) == 1 else None
    report["source"]["template_guid"] = (
        master.raw_fields[13] if master and len(master.raw_fields) > 13 else None
    )
    target_spec = _target(master, diagnostics)
    validate_template_passes(ase, master, diagnostics, report)
    if master and any(w.in_node == master.node_id and int(w.in_port) in {4, 7} for w in ase.graph.wires):
        target_spec.setdefault("options", {})["alphaClip"] = True

    compiled, asset_map = compiled_properties(ase.prefix), load_asset_map(asset_map_path)
    nodes, properties, mappings, handled, failed = [], [], {}, set(active), set()
    structural = {MASTER_TYPE, WIRE_TYPE, REGISTER_LOCAL_VAR_TYPE, GET_LOCAL_VAR_TYPE, COMMENTARY_TYPE}
    handled.update(n.node_id for n in ase.graph.nodes if n.type_name in structural)
    for node in ase.graph.nodes:
        if node.type_name in structural:
            continue
        try:
            created, props, port_map = convert_node(node, ase.graph.wires, compiled, target, asset_map)
        except (ValueError, IndexError) as exc:
            failed.add(node.node_id)
            handled.add(node.node_id)
            diagnostics.append(diagnostic(node.node_id, "NODE_UNSUPPORTED", str(exc),
                                          "No create-ready specification can be produced"))
            continue
        nodes.extend(created); properties.extend(props); mappings[node.node_id] = port_map; handled.add(node.node_id)
        report["mappings"].append({"source_nodes": [node.node_id],
                                   "target_nodes": [item.target_id for item in created],
                                   "kind": "expanded" if len(created) > 1 else "direct", "ports": []})
    for node in ase.graph.nodes:
        if node.node_id not in handled:
            diagnostics.append(diagnostic(node.node_id, "NODE_UNHANDLED", node.type_name,
                                          "The exporter has no semantic rule"))

    edges = []
    for wire in ase.graph.wires:
        destination = ase.graph.node_by_id(wire.in_node)
        if destination is None or destination.type_name in {WIRE_TYPE, REGISTER_LOCAL_VAR_TYPE}:
            continue
        try:
            source_id, source_port = _resolve_source(ase, incoming, wire.out_node, int(wire.out_port), set())
        except (ValueError, StopIteration) as exc:
            diagnostics.append(diagnostic(wire.out_node, "SOURCE_INVALID", str(exc), "Data dependency is unresolved"))
            continue
        if source_id in failed or wire.in_node in failed:
            continue
        source_end = mappings.get(source_id, {}).get(source_port)
        if destination.type_name == MASTER_TYPE:
            target_end = (MASTER_OUTPUTS.get(int(wire.in_port)), 0)
        else:
            target_end = mappings.get(wire.in_node, {}).get(-1 - int(wire.in_port))
        if not source_end or not target_end or target_end[0] is None:
            diagnostics.append(diagnostic(wire.in_node, "PORT_UNSUPPORTED",
                f"ASE connection {source_id}:{source_port} -> {wire.in_node}:{wire.in_port} has no semantic binding",
                "The computation graph cannot be preserved"))
            continue
        edges.append(SemanticEdge(*source_end, *target_end))
        _record_port(report, source_id, source_port, source_end, wire.in_node, int(wire.in_port), target_end)
    for node in nodes:
        for target_id in node.source_ids:
            edges.append(SemanticEdge(node.target_id, 0, target_id, -1))
    groups_spec = groups(ase, mappings, diagnostics)
    properties = unique_properties(properties, diagnostics)
    verify_texture_dependencies(ase, source, target, properties, nodes, report, diagnostics)
    reconcile_shaderlab_properties(compiled, properties, report, diagnostics)
    inspector_degradations(ase, properties, report)
    report["verification"]["source_parse"] = status("passed", f"{len(ase.graph.nodes)} nodes, {len(ase.graph.wires)} wires")
    report["verification"]["source_structure"] = status(
        "failed" if structural_errors else "passed",
        f"{len(structural_errors)} error(s), {report['source_validation']['warning_count']} warning(s)",
    )
    if diagnostics:
        report["verification"]["semantic_mapping"] = status("blocked", f"{len(diagnostics)} diagnostic(s)")
        raise ExportError("ASE graph contains unsupported or ambiguous semantics", report)
    candidate = {"schema": "sgcli.native.v2", "name": name or f"Converted/{source.stem}",
                 "graph_kind": "main", "graph_settings": {"precision": _graph_precision(master)},
                 "target": target_spec, "properties": properties,
                 "nodes": [node.candidate() for node in nodes], "connections": []}
    if groups_spec:
        candidate["groups"] = groups_spec
    report["verification"]["semantic_mapping"] = status("passed", f"{len(nodes)} target nodes, {len(edges)} semantic connections")
    return candidate, report, nodes, edges


def _resolve_source(ase, incoming, node_id, port, seen):
    key = (node_id, port)
    if key in seen:
        raise ValueError(f"data-flow cycle reaches node {node_id}")
    seen.add(key)
    node = ase.graph.node_by_id(node_id)
    if node is None:
        raise ValueError(f"source node {node_id} does not exist")
    if node.type_name == GET_LOCAL_VAR_TYPE:
        item = parse_get_local_var(node)
        register = ase.graph.node_by_id(item["register_id"])
        if register is None or register.type_name != REGISTER_LOCAL_VAR_TYPE:
            raise ValueError(f"Get Local Var {node_id} references missing register {item['register_id']}")
        wire = incoming.get((register.node_id, 0))
        if wire is None:
            raise ValueError(f"Register Local Var {register.node_id} has no source")
        return _resolve_source(ase, incoming, wire.out_node, int(wire.out_port), seen)
    if node.type_name in {WIRE_TYPE, REGISTER_LOCAL_VAR_TYPE}:
        wire = incoming.get((node_id, 0))
        if wire is None:
            raise ValueError(f"structural node {node_id} has no source")
        return _resolve_source(ase, incoming, wire.out_node, int(wire.out_port), seen)
    return node_id, port


def _target(master, diagnostics):
    if master is None:
        return {"model": "Unlit", "surface": "Opaque", "blend": "Alpha", "two_sided": False}
    fields = master.raw_fields
    if len(fields) < 16 or fields[13] != URP_UNLIT_GUID:
        diagnostics.append(diagnostic(master.node_id, "TARGET_UNSUPPORTED",
            "only the certified standard URP Unlit template is supported", "Target semantics cannot be preserved"))
    if any("UniversalMaterialType=Lit" in value for value in fields):
        diagnostics.append(diagnostic(master.node_id, "TARGET_UNSUPPORTED", "URP Lit mapping is not certified",
                                      "Lighting output semantics cannot be preserved"))
    surface = _template_option(fields, "Surface", ("Opaque", "Transparent"), diagnostics, master.node_id)
    blend = _template_option(fields, "  Blend", ("Alpha", "Premultiply", "Additive", "Multiply"),
                             diagnostics, master.node_id)
    face = _template_option(fields, "Two Sided", ("On", "Cull Back", "Cull Front"), diagnostics,
                            master.node_id)
    if face == "Cull Front":
        diagnostics.append(diagnostic(master.node_id, "CULL_UNSUPPORTED", face,
                                      "Back-face-only rendering requires an unverified renderFace binding"))
    target = {"model": "Unlit", "surface": surface or "Opaque", "blend": blend or "Alpha",
              "two_sided": face == "On"}
    options = {
        "castShadows": _template_bool(fields, "Cast Shadows", diagnostics, master.node_id),
        "receiveShadows": _template_bool(fields, "Receive Shadows", diagnostics, master.node_id),
        "supportsLodCrossFade": _template_bool(fields, "LOD CrossFade", diagnostics, master.node_id),
    }
    for label, certified in {
        "Forward Only": False,
        "  Use Shadow Threshold": False,
        "GPU Instancing": True,
        "Built-in Fog": True,
        "Extra Pre Pass": False,
        "Tessellation": False,
    }.items():
        actual = _template_bool(fields, label, diagnostics, master.node_id)
        if actual is not None and actual is not certified:
            diagnostics.append(diagnostic(master.node_id, "TARGET_OPTION_UNSUPPORTED",
                {"option": label, "value": actual},
                "The selected ASE Master behavior has no certified SG Target equivalent"))
    if "Write Depth" in fields:
        index = fields.index("Write Depth")
        diagnostics.append(diagnostic(master.node_id, "TARGET_OPTION_UNSUPPORTED",
            {"option": "Write Depth", "value": fields[index + 1] if index + 1 < len(fields) else None},
            "ASE depth-write enum mapping is not certified for the supported Unlit template"))
    if all(value is not None for value in options.values()):
        target["options"] = options
    return target


def _template_option(fields, label, choices, diagnostics, node_id):
    matches = [index for index, value in enumerate(fields[:-1]) if value == label]
    if len(matches) != 1:
        diagnostics.append(diagnostic(node_id, "TARGET_OPTION_UNKNOWN", label,
                                      "The active ASE Master option cannot be decoded"))
        return None
    raw = fields[matches[0] + 1]
    try:
        index = int(raw)
    except ValueError:
        index = -1
    if not 0 <= index < len(choices):
        diagnostics.append(diagnostic(node_id, "TARGET_OPTION_UNKNOWN", {"option": label, "value": raw},
                                      "The active ASE Master option is outside the certified range"))
        return None
    return choices[index]


def _template_bool(fields, label, diagnostics, node_id):
    value = _template_option(fields, label, (False, True), diagnostics, node_id)
    return value




def _graph_precision(master):
    return "Half" if master and len(master.raw_fields) > 4 and master.raw_fields[4] == "Half" else "Single"


def _record_port(report, source_id, source_port, source_end, target_id, target_port, target_end):
    for row in report["mappings"]:
        if source_id in row["source_nodes"]:
            row["ports"].append({"source": [source_id, source_port], "target": list(source_end)})
        if target_id in row["source_nodes"]:
            row["ports"].append({"source": [target_id, target_port], "target": list(target_end)})
