"""REG-0031: build reproducibility diagnostics and checkout isolation."""

from __future__ import annotations

import io
import json
from pathlib import Path
import subprocess
import sys
import tarfile


ROOT = Path(__file__).parents[1]
SCRIPT = ROOT / "tools" / "compare_build_artifacts.py"


def _write_tar(path: Path, contents: bytes) -> None:
    with tarfile.open(path, "w:gz") as archive:
        info = tarfile.TarInfo("asecli-0.1.0/payload.txt")
        info.size = len(contents)
        info.mtime = 1788220800
        archive.addfile(info, io.BytesIO(contents))


def _run(left: Path, right: Path, output: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), "--left", str(left), "--right", str(right), "--output", str(output)],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )


def test_identical_build_artifacts_pass_with_hash_and_archive_manifest(tmp_path):
    left = tmp_path / "left"
    right = tmp_path / "right"
    left.mkdir()
    right.mkdir()
    for directory in (left, right):
        (directory / "asecli-0.1.0-py3-none-any.whl").write_bytes(b"same-wheel")
        _write_tar(directory / "asecli-0.1.0.tar.gz", b"same-sdist")
    output = tmp_path / "report.json"
    proc = _run(left, right, output)
    report = json.loads(output.read_text(encoding="utf-8"))
    assert proc.returncode == 0
    assert report["ok"] is True
    assert all(item["equal"] for item in report["artifacts"])
    sdist = next(item for item in report["artifacts"] if item["name"].endswith(".tar.gz"))
    assert sdist["archive"]["first_manifest_difference"] is None
    assert sdist["archive"]["left_manifest"][0]["content_sha256"]


def test_mismatched_sdist_fails_and_persists_first_member_difference(tmp_path):
    left = tmp_path / "left"
    right = tmp_path / "right"
    left.mkdir()
    right.mkdir()
    (left / "asecli-0.1.0-py3-none-any.whl").write_bytes(b"same-wheel")
    (right / "asecli-0.1.0-py3-none-any.whl").write_bytes(b"same-wheel")
    _write_tar(left / "asecli-0.1.0.tar.gz", b"left")
    _write_tar(right / "asecli-0.1.0.tar.gz", b"right")
    output = tmp_path / "report.json"
    proc = _run(left, right, output)
    report = json.loads(output.read_text(encoding="utf-8"))
    assert proc.returncode == 1
    assert report["ok"] is False
    sdist = next(item for item in report["artifacts"] if item["name"].endswith(".tar.gz"))
    difference = sdist["archive"]["first_manifest_difference"]
    assert difference["fields"]["content_sha256"]["left"] != difference["fields"]["content_sha256"]["right"]


def test_ci_build_outputs_live_outside_checkout_and_backend_is_locked():
    workflow = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    project = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert "ASECLI_BUILD_A=$RUNNER_TEMP/asecli-build-a" in workflow
    assert "ASECLI_BUILD_B=$RUNNER_TEMP/asecli-build-b" in workflow
    assert '>> "$GITHUB_ENV"' in workflow
    assert "ASECLI_VERSION=$(uv version --short)" in workflow
    assert "compare_build_artifacts.py" in workflow
    assert "--no-build-isolation" in workflow
    assert 'dist/asecli-$ASECLI_VERSION-py3-none-any.whl' in workflow
    assert 'dist/asecli-$ASECLI_VERSION.spdx.json' in workflow
    assert "name: asecli-${{ env.ASECLI_VERSION }}-python-${{ runner.arch }}" in workflow
    assert "dist/asecli-0.1.0" not in workflow
    assert 'requires = ["hatchling==1.32.0"]' in project
