"""The distributable Agent Skill must install safely and remain versioned."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest


ROOT = Path(__file__).parents[1]
SRC = str(ROOT / "src")


def run(skill_root: Path) -> tuple[int, dict]:
    return run_command("install-skill", "--skill-root", str(skill_root))


def run_command(
    *args: str,
    home: Path | None = None,
    env_overrides: dict[str, str] | None = None,
) -> tuple[int, dict]:
    env = dict(os.environ)
    env["PYTHONPATH"] = SRC
    if home is not None:
        env["HOME"] = str(home)
        env.pop("CODEX_HOME", None)
    if env_overrides:
        env.update(env_overrides)
    proc = subprocess.run(
        [sys.executable, "-m", "asecli.cli.main", *args],
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


def test_install_skill_without_routing_options_keeps_legacy_codex_default(tmp_path):
    code, payload = run_command("install-skill", home=tmp_path)
    assert code == 0
    assert payload["data"]["agent"] == "codex"
    assert payload["data"]["path"] == str(tmp_path / ".codex/skills/asecli")


def test_install_skill_without_routing_options_keeps_codex_home_override(tmp_path):
    codex_home = tmp_path / "custom-codex"
    code, payload = run_command(
        "install-skill",
        home=tmp_path,
        env_overrides={"CODEX_HOME": str(codex_home)},
    )
    assert code == 0
    assert payload["data"]["path"] == str(codex_home / "skills/asecli")


@pytest.mark.parametrize(
    ("agent", "relative_root"),
    [
        ("agents", ".agents/skills"),
        ("codex", ".agents/skills"),
        ("claude", ".claude/skills"),
        ("cursor", ".cursor/skills"),
        ("gemini", ".gemini/skills"),
        ("copilot", ".github/skills"),
    ],
)
def test_install_skill_supports_mainstream_project_destinations(tmp_path, agent, relative_root):
    project = tmp_path / "project"
    code, payload = run_command(
        "install-skill",
        "--agent",
        agent,
        "--scope",
        "project",
        "--project-root",
        str(project),
    )
    assert code == 0
    assert payload["data"]["agent"] == agent
    assert payload["data"]["scope"] == "project"
    assert payload["data"]["path"] == str(project / relative_root / "asecli")
    assert (project / relative_root / "asecli/SKILL.md").is_file()


@pytest.mark.parametrize(
    ("agent", "relative_root"),
    [
        ("agents", ".agents/skills"),
        ("codex", ".agents/skills"),
        ("claude", ".claude/skills"),
        ("cursor", ".cursor/skills"),
        ("gemini", ".gemini/skills"),
        ("copilot", ".copilot/skills"),
    ],
)
def test_install_skill_supports_mainstream_user_destinations(tmp_path, agent, relative_root):
    code, payload = run_command("install-skill", "--agent", agent, home=tmp_path)
    assert code == 0
    assert payload["data"]["path"] == str(tmp_path / relative_root / "asecli")
    assert (tmp_path / relative_root / "asecli/SKILL.md").is_file()


def test_install_skill_agent_all_uses_minimal_non_duplicate_roots(tmp_path):
    code, payload = run_command("install-skill", "--agent", "all", home=tmp_path)
    assert code == 0
    data = payload["data"]
    assert data["agent"] == "all"
    assert data["installed_count"] == 2
    assert data["compatible_agents"] == [
        "codex",
        "claude-code",
        "cursor",
        "gemini-cli",
        "github-copilot",
    ]
    assert {target["path"] for target in data["targets"]} == {
        str(tmp_path / ".agents/skills/asecli"),
        str(tmp_path / ".claude/skills/asecli"),
    }
    assert data["targets"][0]["compatible_agents"] == [
        "codex",
        "cursor",
        "gemini-cli",
        "github-copilot",
    ]


def test_install_skill_agent_all_preflights_every_conflict_before_writing(tmp_path):
    conflict = tmp_path / ".claude/skills/asecli"
    conflict.mkdir(parents=True)
    (conflict / "SKILL.md").write_text("---\nname: asecli\n---\nforeign", encoding="utf-8")

    code, payload = run_command("install-skill", "--agent", "all", home=tmp_path)
    assert code == 2
    assert payload["error"]["code"] == "SKILL_INSTALL_CONFLICT"
    assert not (tmp_path / ".agents/skills/asecli").exists()


def test_install_skill_rejects_project_root_for_user_scope(tmp_path):
    code, payload = run_command(
        "install-skill",
        "--agent",
        "agents",
        "--project-root",
        str(tmp_path),
        home=tmp_path,
    )
    assert code == 2
    assert payload["error"]["code"] == "SKILL_INSTALL_ERROR"


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
