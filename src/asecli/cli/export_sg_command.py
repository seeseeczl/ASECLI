"""CLI orchestration for strict ASE -> SGCLI native v2 export."""

from __future__ import annotations

import json
import os
from pathlib import Path
import tempfile
import hashlib

from ..export_sg import ExportError, SgcliAdapter, bind_configured_ports, build_candidate, validate_schema
from ..sg_export.model import report_template, status
from .commands import CliError


def configure_export_sg_parser(sub) -> None:
    parser = sub.add_parser("export-sg", help="export an ASE shader as a strict sgcli.native.v2 creation spec")
    parser.add_argument("file")
    parser.add_argument("--target-project", required=True)
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--name")
    parser.add_argument("--asset-map")
    parser.add_argument("--sgcli-bin", default="sgcli")
    parser.add_argument("--sg-schema", help="formal sgcli.native.v2 JSON Schema; defaults to the bundled contract snapshot")
    parser.add_argument("--mcp-url", default="http://127.0.0.1:9080/mcp")
    parser.add_argument("--ase-mcp-url", help="reserved for source-side opaque semantic inspection")
    parser.add_argument("--write", action="store_true")
    parser.set_defaults(func=cmd_export_sg)


def cmd_export_sg(args) -> dict:
    source = Path(args.file).resolve()
    target = Path(args.target_project).resolve()
    out = Path(args.out_dir).resolve()
    if not source.is_file():
        raise CliError("NOT_FOUND", f"file not found: {source}")
    if not (target / "Assets").is_dir() or not (target / "ProjectSettings").is_dir():
        raise CliError("USAGE_ERROR", f"target project is not a Unity project: {target}")
    if args.write and not out.is_dir():
        raise CliError("NOT_FOUND", f"output directory not found: {out}")
    graph_path = out / "graph.sg.json"
    report_path = out / "report.json"
    if args.write and (graph_path.exists() or report_path.exists()):
        raise CliError("WRITE_CONFLICT", "export never overwrites generated output files")

    report = None
    try:
        candidate, report, nodes, edges = build_candidate(source, target, name=args.name, asset_map_path=args.asset_map)
        adapter = SgcliAdapter(args.sgcli_bin, args.mcp_url)
        doctor = adapter.doctor()
        report["target_environment"]["doctor"] = doctor
        if Path(doctor.get("project", "")).resolve() != target:
            raise RuntimeError(f"SGCLI Editor project mismatch: {doctor.get('project')} != {target}")
        if doctor.get("supported") is not True or doctor.get("urp_available") is not True:
            raise RuntimeError("SGCLI doctor reports an unsupported Shader Graph/URP environment")
        catalog = adapter.catalog()
        configured = adapter.configured(candidate)
        spec = bind_configured_ports(candidate, report, nodes, edges, configured)
        try:
            schema_path, schema_hash = validate_schema(spec, args.sg_schema)
        except (OSError, ValueError, RuntimeError, json.JSONDecodeError) as exc:
            report["verification"]["schema"] = status("failed", str(exc))
            raise
        report["receiver_schema"].update(path=schema_path, sha256=schema_hash)
        report["verification"]["schema"] = {"status": "passed", "evidence": "Draft 2020-12 validation passed"}
        target_contract = configured.get("target_contract", {})
        try:
            precheck = adapter.precheck(spec, catalog, target_contract.get("outputs"))
        except (OSError, ValueError, RuntimeError, json.JSONDecodeError) as exc:
            report["verification"]["python_precheck"] = status("failed", str(exc))
            raise
        report["verification"]["python_precheck"] = {
            "status": "passed", "evidence": precheck,
        }
        preview_asset = target / "Assets" / "ASECLI-Export-Preview" / f"{source.stem}.shadergraph"
        try:
            preview = adapter.preview(preview_asset, spec)
        except (OSError, ValueError, RuntimeError, json.JSONDecodeError) as exc:
            report["verification"]["create_preview"] = status("failed", str(exc))
            raise
        report["verification"]["create_preview"] = {
            "status": "passed", "evidence": _stable_preview_evidence(preview),
        }
        current_hash = hashlib.sha256(source.read_bytes()).hexdigest()
        if current_hash != report["source"]["sha256"]:
            raise RuntimeError("source Shader changed during export")
    except ExportError as exc:
        report = exc.report
        _write_failure_report(args.write, report_path, report)
        raise CliError("SG_EXPORT_BLOCKED", str(exc), {"report": report, "report_json": str(report_path) if args.write else None}) from exc
    except (OSError, ValueError, RuntimeError, json.JSONDecodeError) as exc:
        if report is None:
            report = _source_failure_report(source, target, exc)
            _write_failure_report(args.write, report_path, report)
            raise CliError("SG_EXPORT_BLOCKED", str(exc), {
                "report": report, "report_json": str(report_path) if args.write else None,
            }) from exc
        report["diagnostics"].append({"source_node_id": None, "code": "TARGET_VALIDATION_FAILED", "reason": str(exc), "impact": "No create-ready specification was produced"})
        if report["verification"]["target_capabilities"]["status"] == "not_run":
            report["verification"]["target_capabilities"] = {"status": "blocked", "evidence": str(exc)}
        _write_failure_report(args.write, report_path, report)
        raise CliError("SG_EXPORT_BLOCKED", str(exc), {"report": report, "report_json": str(report_path) if args.write else None}) from exc

    write_result = _write_pair(graph_path, spec, report) if args.write else None
    result = {
        "written": bool(args.write), "graph_json": str(graph_path) if args.write else None,
        "report_json": str(report_path) if args.write else None,
        "node_count": len(spec["nodes"]), "connection_count": len(spec["connections"]),
        "source_sha256": report["source"]["sha256"], "validation": report["verification"],
    }
    if write_result is not None:
        result["write"] = write_result
    return result


def _write_failure_report(write: bool, path: Path, report: dict) -> None:
    if not write:
        return
    if path.exists():
        raise CliError("WRITE_CONFLICT", f"export report already exists: {path}")
    _write_new(path, report)


def _source_failure_report(source: Path, target: Path, exc: Exception) -> dict:
    try:
        raw = source.read_bytes()
    except OSError:
        raw = b""
    text = raw.decode("utf-8", errors="replace")
    report = report_template(source, target, "unknown", text)
    report["source"]["sha256"] = hashlib.sha256(raw).hexdigest()
    report["diagnostics"].append({
        "source_node_id": None, "code": "SOURCE_READ_FAILED", "reason": str(exc),
        "impact": "ASE semantics could not be decoded",
    })
    report["verification"]["source_parse"] = status("failed", str(exc))
    report["verification"]["source_structure"] = status("blocked", "source parse failed")
    report["verification"]["semantic_mapping"] = status("blocked", "source parse failed")
    return report


def _write_pair(graph_path: Path, graph: dict, report: dict) -> dict:
    report_path = graph_path.with_name("report.json")
    if graph_path.exists() or report_path.exists():
        raise CliError("WRITE_CONFLICT", "export never overwrites generated output files")
    graph_result = _write_new(graph_path, graph)
    try:
        report_result = _write_new(report_path, report)
    except Exception as exc:
        raise CliError(
            "WRITE_PARTIAL",
            "graph was committed but report was not; inspect committed_files before retrying",
            {"committed_files": [graph_result], "report": str(report_path)},
        ) from exc
    return {"committed": True, "files": [graph_result, report_result]}


def _stable_preview_evidence(preview: dict) -> dict:
    keys = (
        "preview", "written", "structure_validated", "editor_graph_validated",
        "editor_validated", "visual_validated", "graph_kind", "target_model",
        "graph_settings", "adaptations",
    )
    evidence = {key: preview[key] for key in keys if key in preview}
    nodes = preview.get("nodes")
    connections = preview.get("connections")
    if isinstance(nodes, list):
        evidence["node_count"] = len(nodes)
    if isinstance(connections, list):
        evidence["connection_count"] = len(connections)
    return evidence


def _write_new(path: Path, value: dict) -> dict:
    encoded = (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    fd, raw = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    temp = Path(raw)
    committed = False
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(encoded)
            handle.flush()
            os.fsync(handle.fileno())
        # Publish with create-if-absent semantics. os.replace would overwrite a
        # file created by another exporter after the initial conflict check.
        os.link(temp, path)
        committed = True
    except FileExistsError as exc:
        raise CliError("WRITE_CONFLICT", f"export file already exists: {path}") from exc
    except OSError as exc:
        raise CliError("WRITE_ERROR", str(exc)) from exc
    finally:
        if not committed:
            try:
                temp.unlink(missing_ok=True)
            except OSError:
                pass

    warnings = []
    temporary_path = None
    try:
        temp.unlink()
    except OSError as exc:
        warnings.append(f"temporary link cleanup failed: {exc}")
        temporary_path = str(temp)
    result = {
        "path": str(path),
        "sha256": hashlib.sha256(encoded).hexdigest(),
        "committed": True,
        "warnings": warnings,
    }
    if temporary_path is not None:
        result["temporary_path"] = temporary_path
    return result
