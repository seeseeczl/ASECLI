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
V031_GUI_PARTS = (
    ROOT / "src/asecli/bridge/resources/asecli_material_gui.part00.cs.txt",
    ROOT / "src/asecli/bridge/resources/asecli_material_gui.part01.cs.txt",
)


def material_only_v031_source() -> bytes:
    source = b"".join(path.read_bytes() for path in V031_GUI_PARTS).decode("utf-8")
    source = source.replace(
        "// ASECLI clean-room implementation of the public MZGUI.MZGUI contract.\n"
        "// New shaders use the native FoldoutMzgui, TooltipMzgui and HelpBoxMzgui names.\n",
        "// ASECLI clean-room material GUI.\n"
        "// Implements ASECLIFoldout, ASECLITooltip, and ASECLIHelpBox metadata for\n"
        "// ASECLI-generated shaders, and reads the three historical MZGUI names.\n",
    )
    source = source.replace("    public interface IASECLIFallbackProvider { }\n", "")
    source = source.replace(
        "public class ASECLIMaterialGUI : ShaderGUI, IASECLIFallbackProvider",
        "public sealed class ASECLIMaterialGUI : ShaderGUI",
    )
    source = source.replace(
        "\n// Portable public entry point. A shader authored in a fallback project keeps\n"
        "// working unchanged when moved to a project containing the native MZGUI package.\n"
        "namespace MZGUI\n{\n"
        "    public sealed class MZGUI : ASECLI.MaterialGUI.ASECLIMaterialGUI { }\n}\n",
        "",
    )
    return source.encode("utf-8")


def authoring_preview_source() -> bytes:
    resources = ROOT / "src/asecli/bridge/resources"
    authoring = b"".join(
        (resources / name).read_bytes()
        for name in (
            "asecli_material_gui.authoring.part00.cs.txt",
            "asecli_material_gui.authoring.part01.cs.txt",
            "asecli_material_gui.hydration.cs.txt",
        )
    ).decode("utf-8")
    authoring = authoring.replace(
        'field.SetValue(master, "MZGUI.MZGUI");',
        'field.SetValue(master, "ASECLI.MaterialGUI.ASECLIMaterialGUI");',
    )
    authoring = authoring.replace(
        'MenuItem("Window/Amplify Shader Editor/MZGUI Attributes (ASECLI)")',
        'MenuItem("Window/Amplify Shader Editor/GUI Attributes (ASECLI)")',
    )
    authoring = authoring.replace(
        'new GUIContent("MZGUI Attributes")', 'new GUIContent("ASE GUI Attributes")'
    )
    authoring = authoring.replace(
        '"使用 MZGUI.MZGUI 材质面板"', '"使用 ASECLI 兼容材质面板"'
    )
    return material_only_v031_source() + authoring.encode("utf-8")


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


def test_material_only_v031_gui_upgrades_to_the_editor_authoring_adapter(tmp_path):
    project = unity_project(tmp_path)
    target = project / GUI_SUPPORT_ASSET_PATH
    target.parent.mkdir(parents=True)
    previous = material_only_v031_source()
    digest = hashlib.sha256(previous).hexdigest()
    assert GUI_SUPPORT_KNOWN_PREVIOUS[digest] == "0.3.1-material-only"
    target.write_bytes(previous)

    upgraded = install_gui_support(project, write=True)

    assert upgraded["written"] is True
    assert target.read_text(encoding="utf-8") == GUI_SUPPORT_SOURCE
    assert Path(upgraded["backup"]).read_bytes() == previous
    assert not target.with_name(target.name + ".asecli-upgrade.tmp").exists()


def test_authoring_preview_upgrades_to_the_portable_mzgui_editor_name(tmp_path):
    project = unity_project(tmp_path)
    target = project / GUI_SUPPORT_ASSET_PATH
    target.parent.mkdir(parents=True)
    previous = authoring_preview_source()
    digest = hashlib.sha256(previous).hexdigest()
    assert GUI_SUPPORT_KNOWN_PREVIOUS[digest] == "0.3.1-authoring-preview"
    target.write_bytes(previous)

    upgraded = install_gui_support(project, write=True)

    assert upgraded["recommended_editor"] == "MZGUI.MZGUI"
    assert target.read_text(encoding="utf-8") == GUI_SUPPORT_SOURCE
    assert Path(upgraded["backup"]).read_bytes() == previous


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
