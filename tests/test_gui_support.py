"""REG-0030/REG-0035: ASECLI material GUI installation contract."""

from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

from asecli.bridge.gui_support import (
    GUI_SUPPORT_ASSET_PATH,
    GUI_SUPPORT_SHA256,
    GUI_SUPPORT_SOURCE,
    inspect_gui_support,
    install_gui_support,
)
from asecli.core import ASECLI_GUI_EDITOR


ROOT = Path(__file__).parents[1]
SRC = str(ROOT / "src")


def unity_project(tmp_path: Path) -> Path:
    project = tmp_path / "UnityProject"
    (project / "Assets").mkdir(parents=True)
    (project / "ProjectSettings").mkdir()
    return project


def run_cli(*args: str) -> tuple[int, dict]:
    env = dict(os.environ)
    env["PYTHONPATH"] = SRC
    proc = subprocess.run(
        [sys.executable, "-m", "asecli.cli.main", *args],
        capture_output=True,
        text=True,
        env=env,
    )
    lines = proc.stdout.splitlines()
    assert len(lines) == 1, (proc.stdout, proc.stderr)
    return proc.returncode, json.loads(lines[0])


def test_packaged_source_defines_asecli_metadata_and_legacy_read_compatibility():
    assert "class ASECLIMaterialGUI : ShaderGUI" in GUI_SUPPORT_SOURCE
    assert "class ASECLIFoldoutDecorator" in GUI_SUPPORT_SOURCE
    assert "class ASECLITooltipDecorator" in GUI_SUPPORT_SOURCE
    assert "class ASECLIHelpBoxDecorator" in GUI_SUPPORT_SOURCE
    assert "class FoldoutMzguiDecorator" in GUI_SUPPORT_SOURCE
    assert "class TooltipMzguiDecorator" in GUI_SUPPORT_SOURCE
    assert "class HelpBoxMzguiDecorator" in GUI_SUPPORT_SOURCE
    assert "ASECLI never writes these names" in GUI_SUPPORT_SOURCE
    assert "GetShaderPropertyAttributes" in GUI_SUPPORT_SOURCE
    assert "new Material(shader)" in GUI_SUPPORT_SOURCE
    assert "GetAssetDependencyHash" in GUI_SUPPORT_SOURCE
    assert '"intValue", BindingFlags.Public' in GUI_SUPPORT_SOURCE
    assert '"ASECLIFoldout"' in GUI_SUPPORT_SOURCE
    assert '"ASECLITooltip"' in GUI_SUPPORT_SOURCE
    assert '"ASECLIHelpBox"' in GUI_SUPPORT_SOURCE
    assert '"FoldoutMzgui"' in GUI_SUPPORT_SOURCE
    assert 'public string MetadataType { get { return "TooltipMzgui"; } }' in GUI_SUPPORT_SOURCE
    assert 'public string MetadataType { get { return "HelpBoxMzgui"; } }' in GUI_SUPPORT_SOURCE
    assert "TryReadSourceMetadata" in GUI_SUPPORT_SOURCE
    assert "File.ReadAllText(fullPath)" in GUI_SUPPORT_SOURCE
    assert "MergeMissingMetadata(metadata, sourceMetadata)" in GUI_SUPPORT_SOURCE
    assert "private static readonly Dictionary<string, bool> foldoutStates" in GUI_SUPPORT_SOURCE
    assert "AmplifyShaderEditor" not in GUI_SUPPORT_SOURCE


def test_inspect_and_dry_run_do_not_create_project_files(tmp_path):
    project = unity_project(tmp_path)
    target = project / GUI_SUPPORT_ASSET_PATH
    state = inspect_gui_support(project)
    assert state["provider"] == "missing"
    assert state["recommended_editor"] == ASECLI_GUI_EDITOR
    assert state["capabilities"]["foldout"] == "ASECLIFoldout"
    assert state["capabilities"]["legacy_read_compatibility"] == [
        "FoldoutMzgui", "TooltipMzgui", "HelpBoxMzgui"
    ]
    assert state["would_write"] is True
    planned = install_gui_support(project)
    assert planned["action"] == "install_asecli_material_gui"
    assert not target.exists()


def test_write_installs_exact_resource_and_is_idempotent(tmp_path):
    project = unity_project(tmp_path)
    target = project / GUI_SUPPORT_ASSET_PATH
    installed = install_gui_support(project, write=True)
    assert installed["provider"] == "asecli_compat"
    assert installed["recommended_editor"] == ASECLI_GUI_EDITOR
    assert installed["written"] is True
    assert installed["requires_editor_recompile"] is True
    assert target.read_text(encoding="utf-8") == GUI_SUPPORT_SOURCE
    assert installed["asecli_material_gui"]["actual_sha256"] == GUI_SUPPORT_SHA256

    repeated = install_gui_support(project, write=True)
    assert repeated["action"] == "already_installed"
    assert repeated["written"] is False


def test_native_mzgui_artifacts_do_not_block_asecli_installation(tmp_path):
    project = unity_project(tmp_path)
    native = project / "Assets/Legacy/MZGUI.cs"
    native.parent.mkdir(parents=True)
    native.write_text("namespace MZGUI { class MZGUI {} }", encoding="utf-8")

    installed = install_gui_support(project, write=True)
    assert installed["provider"] == "asecli_compat"
    assert installed["recommended_editor"] == ASECLI_GUI_EDITOR
    assert (project / GUI_SUPPORT_ASSET_PATH).exists()


def test_existing_different_target_is_never_overwritten(tmp_path):
    project = unity_project(tmp_path)
    target = project / GUI_SUPPORT_ASSET_PATH
    target.parent.mkdir(parents=True)
    original = "// user-owned GUI\n"
    target.write_text(original, encoding="utf-8")
    state = inspect_gui_support(project)
    assert state["provider"] == "target_conflict"
    assert state["recommended_editor"] is None
    with pytest.raises(FileExistsError, match="refusing to overwrite"):
        install_gui_support(project, write=True)
    assert target.read_text(encoding="utf-8") == original


def test_symlink_target_is_treated_as_conflict(tmp_path):
    project = unity_project(tmp_path)
    target = project / GUI_SUPPORT_ASSET_PATH
    target.parent.mkdir(parents=True)
    outside = tmp_path / "outside.cs"
    outside.write_text("// outside\n", encoding="utf-8")
    target.symlink_to(outside)
    with pytest.raises(ValueError, match="escapes through a symbolic link"):
        inspect_gui_support(project)
    assert outside.read_text(encoding="utf-8") == "// outside\n"


def test_install_refuses_a_target_that_appears_during_the_write(tmp_path, monkeypatch):
    project = unity_project(tmp_path)
    target = project / GUI_SUPPORT_ASSET_PATH
    target.parent.mkdir(parents=True)
    original_open = os.open

    def competing_open(path, flags, mode=0o777, *, dir_fd=None):
        if Path(path).name == target.name and flags & os.O_EXCL:
            target.write_text("// concurrent content\n", encoding="utf-8")
        return original_open(path, flags, mode, dir_fd=dir_fd)

    monkeypatch.setattr("asecli.bridge.gui_support.os.open", competing_open)
    with pytest.raises(FileExistsError, match="appeared during installation"):
        install_gui_support(project, write=True)
    assert target.read_text(encoding="utf-8") == "// concurrent content\n"


@pytest.mark.skipif(
    os.open not in os.supports_dir_fd or os.mkdir not in os.supports_dir_fd or not hasattr(os, "O_NOFOLLOW"),
    reason="secure directory-descriptor installation is unavailable on this platform",
)
def test_install_refuses_parent_symlink_swap_without_writing_outside_project(tmp_path, monkeypatch):
    project = unity_project(tmp_path)
    target = project / GUI_SUPPORT_ASSET_PATH
    outside = tmp_path / "outside"
    outside.mkdir()
    original_open = os.open

    def competing_open(path, flags, mode=0o777, *, dir_fd=None):
        if Path(path).name == target.name and flags & os.O_EXCL:
            target.parent.rmdir()
            target.parent.symlink_to(outside, target_is_directory=True)
        return original_open(path, flags, mode, dir_fd=dir_fd)

    monkeypatch.setattr("asecli.bridge.gui_support.os.open", competing_open)
    with pytest.raises(RuntimeError, match="directory changed during installation"):
        install_gui_support(project, write=True)
    assert not (outside / target.name).exists()


def test_cli_dry_run_write_and_conflict_are_single_json(tmp_path):
    project = unity_project(tmp_path)
    code, payload = run_cli("gui-support", str(project))
    assert code == 0
    assert payload["data"]["provider"] == "missing"
    assert payload["data"]["written"] is False

    code, payload = run_cli("gui-support", str(project), "--write")
    assert code == 0
    assert payload["data"]["provider"] == "asecli_compat"
    assert payload["data"]["written"] is True

    target = project / GUI_SUPPORT_ASSET_PATH
    target.write_text("// changed by project\n", encoding="utf-8")
    code, payload = run_cli("gui-support", str(project), "--write")
    assert code == 2
    assert payload["error"]["code"] == "GUI_SUPPORT_ERROR"


def test_cli_no_longer_accepts_the_removed_runtime_probe_option(tmp_path):
    code, payload = run_cli("gui-support", str(unity_project(tmp_path)), "--runtime-probe")
    assert code == 2
    assert payload["error"]["code"] == "USAGE_ERROR"


def test_project_shape_is_validated_before_any_write(tmp_path):
    project = tmp_path / "NotUnity"
    project.mkdir()
    code, payload = run_cli("gui-support", str(project), "--write")
    assert code == 2
    assert payload["error"]["code"] == "GUI_SUPPORT_ERROR"
    assert not (project / "Assets").exists()
