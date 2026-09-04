"""The distributable Agent Skill must install safely and remain versioned."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path


ROOT = Path(__file__).parents[1]
SRC = str(ROOT / "src")


def run(skill_root: Path) -> tuple[int, dict]:
    env = dict(os.environ)
    env["PYTHONPATH"] = SRC
    proc = subprocess.run(
        [sys.executable, "-m", "asecli.cli.main", "install-skill", "--skill-root", str(skill_root)],
        capture_output=True,
        text=True,
        env=env,
    )
    return proc.returncode, json.loads(proc.stdout)


def test_install_skill_copies_the_full_packaged_source_and_is_idempotent(tmp_path):
    skill_root = tmp_path / "skills"
    code, payload = run(skill_root)
    assert code == 0
    assert payload["ok"] is True
    assert payload["data"]["status"] == "installed"
    installed = skill_root / "asecli"
    source = ROOT / "skills" / "asecli"
    assert (installed / "SKILL.md").read_bytes() == (source / "SKILL.md").read_bytes()
    assert (installed / "references/layout-standard.md").read_bytes() == (
        source / "references/layout-standard.md"
    ).read_bytes()

    code, payload = run(skill_root)
    assert code == 0
    assert payload["data"]["status"] == "already_installed"
    assert payload["data"]["installed"] is False


def test_install_skill_refuses_to_overwrite_a_different_skill(tmp_path):
    target = tmp_path / "skills" / "asecli"
    target.mkdir(parents=True)
    (target / "SKILL.md").write_text("---\nname: asecli\n---\nforeign", encoding="utf-8")
    code, payload = run(tmp_path / "skills")
    assert code == 2
    assert payload["ok"] is False
    assert payload["error"]["code"] == "SKILL_INSTALL_CONFLICT"
    assert (target / "SKILL.md").read_text(encoding="utf-8") == "---\nname: asecli\n---\nforeign"


def test_wheel_contains_the_full_skill_tree(tmp_path):
    dist = tmp_path / "dist"
    uv = shutil.which("uv")
    assert uv, "uv is required to build the distributable wheel"
    subprocess.run([uv, "build", "--wheel", "--out-dir", str(dist)], cwd=ROOT, check=True)
    wheel = next(dist.glob("asecli-*.whl"))
    with zipfile.ZipFile(wheel) as archive:
        names = set(archive.namelist())
    assert "asecli/skills/asecli/SKILL.md" in names
    assert "asecli/skills/asecli/references/layout-standard.md" in names
