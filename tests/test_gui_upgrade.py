"""REG-0045: known GUI revisions upgrade recoverably and unknown files fail closed."""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from asecli.bridge.gui_support import (
    GUI_SUPPORT_ASSET_PATH,
    GUI_SUPPORT_KNOWN_PREVIOUS,
    GUI_SUPPORT_SOURCE,
    install_gui_support,
)


ROOT = Path(__file__).parents[1]
LEGACY_GUI = ROOT / "tests/fixtures/asecli_material_gui_v0_2_0.cs.txt"


def unity_project(tmp_path: Path) -> Path:
    project = tmp_path / "UnityProject"
    (project / "Assets").mkdir(parents=True)
    (project / "ProjectSettings").mkdir()
    return project


def legacy_target(tmp_path: Path) -> tuple[Path, Path, bytes, str]:
    project = unity_project(tmp_path)
    target = project / GUI_SUPPORT_ASSET_PATH
    target.parent.mkdir(parents=True)
    previous = LEGACY_GUI.read_bytes()
    digest = hashlib.sha256(previous).hexdigest()
    assert digest in GUI_SUPPORT_KNOWN_PREVIOUS
    target.write_bytes(previous)
    return project, target, previous, digest


def test_known_previous_gui_dry_run_reports_upgrade_without_writing(tmp_path):
    project, target, previous, _ = legacy_target(tmp_path)
    planned = install_gui_support(project)

    assert planned["provider"] == "asecli_upgrade_available"
    assert planned["action"] == "upgrade_asecli_material_gui"
    assert planned["would_write"] is True
    assert planned["written"] is False
    assert planned["asecli_material_gui"]["upgrade_available"] is True
    assert planned["asecli_material_gui"]["upgrade_from"] == "0.2.0-original"
    assert target.read_bytes() == previous
    assert not Path(planned["asecli_material_gui"]["backup"]).exists()


def test_known_previous_gui_is_backed_up_and_atomically_upgraded(tmp_path):
    project, target, previous, previous_digest = legacy_target(tmp_path)
    upgraded = install_gui_support(project, write=True)

    backup = Path(upgraded["backup"])
    assert upgraded["action"] == "upgrade_asecli_material_gui"
    assert upgraded["backed_up"] is True
    assert upgraded["written"] is True
    assert target.read_text(encoding="utf-8") == GUI_SUPPORT_SOURCE
    assert backup.read_bytes() == previous
    assert backup.name.endswith(previous_digest[:12])
    assert not target.with_name(target.name + ".asecli-upgrade.tmp").exists()

    repeated = install_gui_support(project, write=True)
    assert repeated["action"] == "already_installed"
    assert backup.read_bytes() == previous


def test_upgrade_refuses_a_conflicting_existing_backup(tmp_path):
    project, target, previous, digest = legacy_target(tmp_path)
    backup = target.with_name(f"{target.name}.asecli-backup-{digest[:12]}")
    backup.write_text("// unrelated backup\n", encoding="utf-8")

    with pytest.raises(FileExistsError, match="backup already exists"):
        install_gui_support(project, write=True)

    assert target.read_bytes() == previous
    assert backup.read_text(encoding="utf-8") == "// unrelated backup\n"


def test_upgrade_refuses_a_symlink_backup(tmp_path):
    project, target, previous, digest = legacy_target(tmp_path)
    outside = tmp_path / "outside.cs"
    outside.write_text("// outside\n", encoding="utf-8")
    backup = target.with_name(f"{target.name}.asecli-backup-{digest[:12]}")
    backup.symlink_to(outside)

    with pytest.raises(OSError):
        install_gui_support(project, write=True)

    assert target.read_bytes() == previous
    assert outside.read_text(encoding="utf-8") == "// outside\n"


def test_upgrade_revalidates_digest_and_preserves_concurrent_content(
    tmp_path, monkeypatch
):
    project, target, previous, _ = legacy_target(tmp_path)
    from asecli.bridge import _gui_resource_upgrade as upgrade

    original_create = upgrade.create_exclusive_resource

    def competing_create(parent_descriptor, name, content, mode):
        opened_stat = original_create(parent_descriptor, name, content, mode)
        if name.endswith(".asecli-upgrade.tmp"):
            target.write_text("// concurrent project edit\n", encoding="utf-8")
        return opened_stat

    monkeypatch.setattr(upgrade, "create_exclusive_resource", competing_create)
    with pytest.raises(FileExistsError, match="changed during upgrade"):
        install_gui_support(project, write=True)

    assert target.read_text(encoding="utf-8") == "// concurrent project edit\n"
    assert not target.with_name(target.name + ".asecli-upgrade.tmp").exists()
    backup = next(target.parent.glob(target.name + ".asecli-backup-*"))
    assert backup.read_bytes() == previous


def test_upgrade_replace_failure_keeps_original_and_recovery_backup(tmp_path, monkeypatch):
    project, target, previous, _ = legacy_target(tmp_path)

    def fail_replace(*args, **kwargs):
        raise OSError("simulated atomic replace failure")

    monkeypatch.setattr("asecli.bridge._gui_resource_upgrade.os.replace", fail_replace)
    with pytest.raises(OSError, match="simulated atomic replace failure"):
        install_gui_support(project, write=True)

    assert target.read_bytes() == previous
    backup = next(target.parent.glob(target.name + ".asecli-backup-*"))
    assert backup.read_bytes() == previous
    assert not target.with_name(target.name + ".asecli-upgrade.tmp").exists()
