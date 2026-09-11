"""Explicit extraction of registered legacy ASECLI-to-SGCLI wrappers."""

from __future__ import annotations

import json
from pathlib import Path

from ..contracts import validate_sgcli_native_spec
from ..schema_validation import SchemaValidationError
from ..sg_export import build_public_report
from .commands import CliError
from .export_sg_command import (
    _ensure_output_directory,
    _receipt_path,
    _write_new,
    _write_pair,
)


SPEC_SUFFIX = ".asecli-to-sgcli.spec.json"
REPORT_SUFFIX = ".asecli-to-sgcli.report.json"
LEGACY_FORMAT = "asecli-graph-report-wrapper-shape"


def configure_migrate_package_parser(sub) -> None:
    parser = sub.add_parser(
        "migrate-package",
        help="explicitly extract a registered legacy wrapper into canonical direct JSON",
    )
    parser.add_argument("input")
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--extract-sg-spec", action="store_true", required=True)
    parser.set_defaults(func=cmd_migrate_package)


def cmd_migrate_package(args) -> dict:
    source = Path(args.input).resolve()
    out = Path(args.out_dir).resolve()
    try:
        source_raw = source.read_bytes()
        value = json.loads(source_raw.decode("utf-8"))
    except OSError as exc:
        raise CliError("NOT_FOUND", str(exc)) from exc
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise CliError("PARSE_ERROR", str(exc)) from exc
    _ensure_output_directory(out)
    stem = _legacy_stem(source)
    spec_path = out / f"{stem}{SPEC_SUFFIX}"
    report_path = out / f"{stem}{REPORT_SUFFIX}"
    receipt_path = _receipt_path(spec_path)
    if spec_path.exists() or report_path.exists() or receipt_path.exists():
        conflict = next(path for path in (spec_path, report_path, receipt_path) if path.exists())
        raise CliError("WRITE_CONFLICT", f"output already exists: {conflict}")
    try:
        spec = _extract(value)
        validate_sgcli_native_spec(spec)
        recheck = source.read_bytes()
        if recheck != source_raw:
            raise ValueError("legacy package changed before publication")
    except (ValueError, SchemaValidationError) as exc:
        report = build_public_report(
            source,
            spec_path,
            None,
            None,
            failure=str(exc),
            source_raw=source_raw,
            source_recheck_raw=_read_if_present(source),
            source_format="legacy-package",
        )
        _write_new(report_path, report)
        raise CliError(
            "VALIDATION_ERROR", str(exc), {"report_json": str(report_path)}
        ) from exc
    report = build_public_report(
        source,
        spec_path,
        spec,
        None,
        source_raw=source_raw,
        source_recheck_raw=recheck,
        producer_schema_validated="passed",
        source_format="legacy-package",
    )
    result = _write_pair(spec_path, spec, report_path, report)
    return {
        "written": True,
        "spec_json": str(spec_path),
        "report_json": str(report_path),
        "receipt_json": str(receipt_path),
        "legacy_format": LEGACY_FORMAT,
        "recognized_shape": {"required_fields": ["graph", "report"]},
        "write": result,
    }


def _extract(value) -> dict:
    if not isinstance(value, dict) or set(value) != {"graph", "report"}:
        raise ValueError("legacy wrapper must contain exactly graph and report")
    if not isinstance(value["report"], dict) or not isinstance(value["graph"], dict):
        raise ValueError("legacy wrapper graph and report must be objects")
    if value["graph"].get("schema") != "sgcli.native.v3":
        raise ValueError("only wrappers containing sgcli.native.v3 can be extracted")
    return value["graph"]


def _legacy_stem(source: Path) -> str:
    return source.stem.removesuffix("-graph-for-sgcli").removesuffix(".sg")


def _read_if_present(source: Path) -> bytes:
    try:
        return source.read_bytes()
    except OSError:
        return b""
