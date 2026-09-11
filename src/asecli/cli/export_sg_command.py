"""CLI orchestration for direct ASECLI -> SGCLI native v3 export."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from ..contracts import validate_sgcli_native_spec
from ..export_sg import ExportError, bind_named_ports, build_candidate
from ..schema_validation import SchemaValidationError
from ..sg_export import assert_spec_publishable, build_public_report
from .commands import CliError
from .conversion_output import (
    receipt_path as _receipt_path,
    write_new as _write_new,
    write_pair as _write_pair,
)


SPEC_SUFFIX = ".asecli-to-sgcli.spec.json"
REPORT_SUFFIX = ".asecli-to-sgcli.report.json"
RECEIPT_SUFFIX = ".asecli-to-sgcli.receipt.json"


def configure_export_sg_parser(sub) -> None:
    parser = sub.add_parser(
        "export-sg",
        help="export an ASE shader as a bare sgcli.native.v3 creation spec",
    )
    parser.add_argument("file")
    parser.add_argument("--out-dir", required=True)
    parser.add_argument(
        "--target-project",
        help="target Unity project; defaults to the project containing the source Shader",
    )
    parser.add_argument("--name")
    parser.add_argument("--asset-map")
    parser.set_defaults(func=cmd_export_sg)


def cmd_export_sg(args) -> dict:
    source = Path(args.file).resolve()
    out = Path(args.out_dir).resolve()
    spec_path, report_path = _conversion_paths(source, out)
    receipt_path = _receipt_path(spec_path)
    if not source.is_file():
        raise CliError("NOT_FOUND", f"file not found: {source}")
    _ensure_output_directory(out)
    if spec_path.exists() or report_path.exists() or receipt_path.exists():
        conflict = next(path for path in (spec_path, report_path, receipt_path) if path.exists())
        raise CliError("WRITE_CONFLICT", f"output already exists: {conflict}")

    try:
        source_raw = source.read_bytes()
    except OSError as exc:
        raise CliError("SG_EXPORT_BLOCKED", f"could not read source Shader: {exc}") from exc
    target = _target_project(source, getattr(args, "target_project", None))
    internal = None
    spec = None
    schema_status = "not_run"
    try:
        if target is None:
            raise ValueError(
                "source is not inside a Unity project; pass --target-project for asset resolution"
            )
        candidate, internal, nodes, edges = build_candidate(
            source,
            target,
            name=getattr(args, "name", None),
            asset_map_path=getattr(args, "asset_map", None),
            source_raw=source_raw,
        )
        spec = bind_named_ports(candidate, internal, nodes, edges)
        _assert_source_unchanged(source, source_raw, "after conversion")
        try:
            validate_sgcli_native_spec(spec)
        except SchemaValidationError as exc:
            schema_status = "failed"
            raise ValueError(f"sgcli.native.v3 schema validation failed: {exc}") from exc
        schema_status = "passed"
        internal["verification"]["schema"] = {
            "status": "passed",
            "evidence": "consumer-owned sgcli.native.v3 schema snapshot",
        }
        report = build_public_report(
            source,
            spec_path,
            spec,
            internal,
            source_raw=source_raw,
            source_recheck_raw=_assert_source_unchanged(
                source, source_raw, "before report construction"
            ),
            producer_schema_validated=schema_status,
        )
        assert_spec_publishable(report)
        _assert_source_unchanged(source, source_raw, "after report construction")
        _assert_source_unchanged(source, source_raw, "before publication")
    except ExportError as exc:
        internal = exc.report
        _write_failure_report(
            source, spec_path, report_path, internal, str(exc),
            source_raw=source_raw, schema_status=schema_status,
        )
        raise CliError(
            "SG_EXPORT_BLOCKED",
            str(exc),
            {"report_json": str(report_path)},
        ) from exc
    except (OSError, ValueError, RuntimeError, json.JSONDecodeError) as exc:
        _write_failure_report(
            source, spec_path, report_path, internal, str(exc),
            source_raw=source_raw, schema_status=schema_status,
        )
        raise CliError(
            "SG_EXPORT_BLOCKED",
            str(exc),
            {"report_json": str(report_path)},
        ) from exc
    write_result = _write_pair(spec_path, spec, report_path, report)
    return {
        "written": True,
        "spec_json": str(spec_path),
        "report_json": str(report_path),
        "receipt_json": str(receipt_path),
        "node_count": len(spec["nodes"]),
        "connection_count": len(spec["connections"]),
        "source_sha256": internal["source"]["sha256"],
        "write": write_result,
    }


def _conversion_paths(source: Path, out: Path) -> tuple[Path, Path]:
    return (
        out / f"{source.stem}{SPEC_SUFFIX}",
        out / f"{source.stem}{REPORT_SUFFIX}",
    )


def _ensure_output_directory(path: Path) -> None:
    try:
        path.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise CliError("WRITE_ERROR", str(exc)) from exc
    if not path.is_dir():
        raise CliError("WRITE_ERROR", f"output path is not a directory: {path}")


def _target_project(source: Path, explicit: str | None) -> Path | None:
    if explicit:
        target = Path(explicit).resolve()
        if not (target / "Assets").is_dir() or not (target / "ProjectSettings").is_dir():
            raise CliError("USAGE_ERROR", f"target project is not a Unity project: {target}")
        return target
    for parent in (source.parent, *source.parents):
        if (parent / "Assets").is_dir() and (parent / "ProjectSettings").is_dir():
            return parent
    return None


def _write_failure_report(
    source: Path,
    spec_path: Path,
    report_path: Path,
    internal: dict | None,
    failure: str,
    *,
    source_raw: bytes,
    schema_status: str,
) -> None:
    if report_path.exists():
        raise CliError("WRITE_CONFLICT", f"output already exists: {report_path}")
    report = build_public_report(
        source,
        spec_path,
        None,
        internal,
        failure=failure,
        source_raw=source_raw,
        source_recheck_raw=_read_source_if_present(source),
        producer_schema_validated=schema_status,
    )
    _write_new(report_path, report)


def _assert_source_unchanged(source: Path, snapshot: bytes, phase: str) -> bytes:
    current = source.read_bytes()
    if current != snapshot:
        raise RuntimeError(
            "source Shader changed " + phase + "; run export again "
            f"(snapshot={hashlib.sha256(snapshot).hexdigest()}, "
            f"recheck={hashlib.sha256(current).hexdigest()})"
        )
    return current


def _read_source_if_present(source: Path) -> bytes:
    try:
        return source.read_bytes()
    except OSError:
        return b""
