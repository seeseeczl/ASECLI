"""Durable create-if-absent JSON publication for conversion artifacts."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import tempfile

from .commands import CliError


SPEC_SUFFIX = ".asecli-to-sgcli.spec.json"
RECEIPT_SUFFIX = ".asecli-to-sgcli.receipt.json"


def write_new(path: Path, value: dict) -> dict:
    encoded = (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    try:
        fd, raw = tempfile.mkstemp(
            prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
        )
    except OSError as exc:
        raise CliError("WRITE_ERROR", str(exc)) from exc
    temp = Path(raw)
    committed = False
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(encoded)
            handle.flush()
            os.fsync(handle.fileno())
        os.link(temp, path)
        committed = True
    except FileExistsError as exc:
        raise CliError("WRITE_CONFLICT", f"output already exists: {path}") from exc
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
    directory_warning = sync_directory(path.parent)
    if directory_warning is not None:
        warnings.append(directory_warning)
    result = {
        "path": str(path), "sha256": hashlib.sha256(encoded).hexdigest(),
        "committed": True, "warnings": warnings,
    }
    if temporary_path is not None:
        result["temporary_path"] = temporary_path
    return result


def sync_directory(directory: Path) -> str | None:
    try:
        descriptor = os.open(directory, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
    except OSError as exc:
        return f"directory sync unavailable: {exc}"
    error = None
    try:
        os.fsync(descriptor)
    except OSError as exc:
        error = exc
    try:
        os.close(descriptor)
    except OSError as exc:
        if error is None:
            error = exc
    return f"directory sync failed: {error}" if error is not None else None


def receipt_path(spec_path: Path) -> Path:
    name = spec_path.name
    if not name.endswith(SPEC_SUFFIX):
        raise CliError("WRITE_ERROR", f"cannot derive receipt name from specification: {spec_path}")
    return spec_path.with_name(name.removesuffix(SPEC_SUFFIX) + RECEIPT_SUFFIX)


def write_pair(spec_path: Path, spec: dict, report_path: Path, report: dict) -> dict:
    final_receipt_path = receipt_path(spec_path)
    if spec_path.exists() or report_path.exists() or final_receipt_path.exists():
        conflict = next(
            path for path in (spec_path, report_path, final_receipt_path) if path.exists()
        )
        raise CliError("WRITE_CONFLICT", f"output already exists: {conflict}")
    report_result = write_new(report_path, report)
    try:
        spec_result = write_new(spec_path, spec)
    except CliError as exc:
        try:
            receipt_result = _write_partial_receipt(
                final_receipt_path, spec_path, report_path, report_result, report
            )
        except CliError as receipt_exc:
            receipt_result = {
                "committed": False,
                "path": str(final_receipt_path),
                "error": receipt_exc.message,
            }
        raise CliError(
            "WRITE_PARTIAL",
            "report was committed but specification was not",
            {
                "report": report_result,
                "specification": str(spec_path),
                "receipt": receipt_result,
            },
        ) from exc
    receipt = _publication_receipt(
        spec_path, report_path, spec_result, report_result, spec_committed=True
    )
    try:
        receipt_result = write_new(final_receipt_path, receipt)
    except CliError as exc:
        raise CliError(
            "WRITE_PARTIAL",
            "specification and report were committed but publication receipt was not",
            {
                "specification": spec_result,
                "report": report_result,
                "receipt": str(final_receipt_path),
            },
        ) from exc
    return {
        "committed": True,
        "files": [spec_result, report_result, receipt_result],
        "receipt": receipt_result,
    }


def _publication_receipt(
    spec_path: Path,
    report_path: Path,
    spec_result: dict,
    report_result: dict,
    *,
    spec_committed: bool,
) -> dict:
    return {
        "schema": "sgcli.conversion-publication-receipt.v1",
        "direction": "asecli-to-sgcli",
        "complete": spec_committed and report_result.get("committed") is True,
        "spec": {
            "path": str(spec_path),
            "sha256": spec_result["sha256"],
            "committed": spec_committed,
        },
        "report": {
            "path": str(report_path),
            "sha256": report_result["sha256"],
            "committed": report_result.get("committed") is True,
        },
    }


def _write_partial_receipt(
    final_receipt_path: Path,
    spec_path: Path,
    report_path: Path,
    report_result: dict,
    report: dict,
) -> dict:
    intended = {
        "path": str(spec_path),
        "sha256": report.get("target", {}).get("sha256", hashlib.sha256(b"").hexdigest()),
    }
    receipt = _publication_receipt(
        spec_path,
        report_path,
        intended,
        report_result,
        spec_committed=False,
    )
    return write_new(final_receipt_path, receipt)
