#!/usr/bin/env python3
"""Compare two build directories and persist reproducibility diagnostics."""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import os
from pathlib import Path
import platform
import sys
import tarfile


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _file_state(path: Path) -> dict:
    return {"path": str(path), "size": path.stat().st_size, "sha256": _sha256(path)}


def _gzip_header(path: Path) -> dict:
    header = path.read_bytes()[:10]
    if len(header) != 10 or header[:2] != b"\x1f\x8b":
        return {"valid": False, "hex": header.hex()}
    return {
        "valid": True,
        "hex": header.hex(),
        "method": header[2],
        "flags": header[3],
        "mtime": int.from_bytes(header[4:8], "little"),
        "extra_flags": header[8],
        "os": header[9],
    }


def _tar_manifest(path: Path) -> list[dict]:
    entries = []
    with tarfile.open(path, "r:gz") as archive:
        for member in archive.getmembers():
            content_sha256 = None
            if member.isfile():
                extracted = archive.extractfile(member)
                if extracted is not None:
                    content_sha256 = hashlib.sha256(extracted.read()).hexdigest()
            entries.append(
                {
                    "name": member.name,
                    "type": member.type.decode("latin-1") if isinstance(member.type, bytes) else str(member.type),
                    "mode": member.mode,
                    "uid": member.uid,
                    "gid": member.gid,
                    "uname": member.uname,
                    "gname": member.gname,
                    "mtime": member.mtime,
                    "size": member.size,
                    "linkname": member.linkname,
                    "content_sha256": content_sha256,
                }
            )
    return entries


def _first_manifest_difference(left: list[dict], right: list[dict]) -> dict | None:
    for index, (left_entry, right_entry) in enumerate(zip(left, right)):
        if left_entry != right_entry:
            keys = sorted(set(left_entry) | set(right_entry))
            fields = {
                key: {"left": left_entry.get(key), "right": right_entry.get(key)}
                for key in keys
                if left_entry.get(key) != right_entry.get(key)
            }
            return {"index": index, "fields": fields}
    if len(left) != len(right):
        return {
            "index": min(len(left), len(right)),
            "fields": {"entry_count": {"left": len(left), "right": len(right)}},
        }
    return None


def compare_directories(left: Path, right: Path) -> dict:
    left_files = {path.name: path for path in left.iterdir() if path.is_file()}
    right_files = {path.name: path for path in right.iterdir() if path.is_file()}
    names = sorted(set(left_files) | set(right_files))
    artifacts = []
    ok = set(left_files) == set(right_files)
    for name in names:
        left_path = left_files.get(name)
        right_path = right_files.get(name)
        item = {"name": name, "left": None, "right": None, "equal": False}
        if left_path is not None:
            item["left"] = _file_state(left_path)
        if right_path is not None:
            item["right"] = _file_state(right_path)
        if left_path is not None and right_path is not None:
            item["equal"] = item["left"]["sha256"] == item["right"]["sha256"]
            if name.endswith(".tar.gz"):
                left_manifest = _tar_manifest(left_path)
                right_manifest = _tar_manifest(right_path)
                item["archive"] = {
                    "left_gzip_header": _gzip_header(left_path),
                    "right_gzip_header": _gzip_header(right_path),
                    "first_manifest_difference": _first_manifest_difference(left_manifest, right_manifest),
                    "left_manifest": left_manifest,
                    "right_manifest": right_manifest,
                }
        ok &= bool(item["equal"])
        artifacts.append(item)
    return {
        "ok": ok,
        "source_date_epoch": os.environ.get("SOURCE_DATE_EPOCH"),
        "python": sys.version,
        "platform": platform.platform(),
        "left": str(left),
        "right": str(right),
        "artifacts": artifacts,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--left", type=Path, required=True)
    parser.add_argument("--right", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if not args.left.is_dir() or not args.right.is_dir():
        parser.error("--left and --right must be existing build directories")
    report = compare_directories(args.left.resolve(), args.right.resolve())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    summary = {
        "ok": report["ok"],
        "output": str(args.output),
        "artifacts": [
            {"name": item["name"], "equal": item["equal"], "left": item["left"], "right": item["right"]}
            for item in report["artifacts"]
        ],
    }
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
