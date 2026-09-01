"""Built-in Unity material GUI detection and installation contract."""

from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

from asecli.bridge.gui_support import (
    ASECLI_GUI_EDITOR,
    GUI_SUPPORT_ASSET_PATH,
    GUI_SUPPORT_SHA256,
    GUI_SUPPORT_SOURCE,
    MZGUI_EDITOR,
    inspect_gui_support,
    install_gui_support,
)


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


def test_packaged_clean_room_source_has_requested_capability_contract():
    assert "class ASECLIMaterialGUI : ShaderGUI" in GUI_SUPPORT_SOURCE
    assert "class FoldoutMzguiDecorator" in GUI_SUPPORT_SOURCE
    assert "class TooltipMzguiDecorator" in GUI_SUPPORT_SOURCE
    assert "class HelpBoxMzguiDecorator" in GUI_SUPPORT_SOURCE
    assert "GetShaderPropertyAttributes" in GUI_SUPPORT_SOURCE
    assert '"变量名: " + propertyName' in GUI_SUPPORT_SOURCE
    assert '默认值: " + defaultValue' in GUI_SUPPORT_SOURCE
    assert "new Material(shader)" in GUI_SUPPORT_SOURCE
    assert "GetAssetDependencyHash" in GUI_SUPPORT_SOURCE
    assert '"intValue", BindingFlags.Public' in GUI_SUPPORT_SOURCE
    assert "Copyright (c) 星纪魅族" not in GUI_SUPPORT_SOURCE
    assert "AmplifyShaderEditor" not in GUI_SUPPORT_SOURCE


def test_inspect_and_dry_run_do_not_create_project_files(tmp_path):
    project = unity_project(tmp_path)
    target = project / GUI_SUPPORT_ASSET_PATH
    state = inspect_gui_support(project)
    assert state["provider"] == "missing"
    assert state["recommended_editor"] == ASECLI_GUI_EDITOR
    assert state["would_write"] is True
    assert state["written"] is False
    planned = install_gui_support(project)
    assert planned["action"] == "install_asecli_compat"
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
    assert installed["asecli_compat"]["actual_sha256"] == GUI_SUPPORT_SHA256

    repeated = install_gui_support(project, write=True)
    assert repeated["action"] == "already_installed"
    assert repeated["written"] is False
    assert target.read_text(encoding="utf-8") == GUI_SUPPORT_SOURCE


def test_native_mzgui_is_preferred_and_not_shadowed(tmp_path):
    project = unity_project(tmp_path)
    native = project / "Assets/AmplifyShaderEditor/MZGUI/Editor/MZGUI.cs"
    native.parent.mkdir(parents=True)
    native.write_text(
        "using UnityEditor; namespace MZGUI { public class MZGUI : ShaderGUI { } }",
        encoding="utf-8",
    )
    state = install_gui_support(project, write=True)
    assert state["provider"] == "native_mzgui"
    assert state["recommended_editor"] == MZGUI_EDITOR
    assert state["action"] == "use_native_mzgui"
    assert state["written"] is False
    assert state["native_mzgui"]["evidence"] == [
        "Assets/AmplifyShaderEditor/MZGUI/Editor/MZGUI.cs"
    ]
    assert not (project / GUI_SUPPORT_ASSET_PATH).exists()


def test_native_and_asecli_providers_fail_closed(tmp_path):
    project = unity_project(tmp_path)
    install_gui_support(project, write=True)
    native = project / "Assets/AmplifyShaderEditor/MZGUI/Editor/MZGUI.cs"
    native.parent.mkdir(parents=True)
    native.write_text(
        "using UnityEditor; namespace MZGUI { public class MZGUI : ShaderGUI { } }",
        encoding="utf-8",
    )

    state = inspect_gui_support(project)
    assert state["provider"] == "multiple"
    assert state["providers"] == ["native_mzgui", "asecli_compat"]
    assert state["recommended_editor"] is None
    with pytest.raises(RuntimeError, match="both installed"):
        install_gui_support(project, write=True)

    code, payload = run_cli("gui-support", str(project), "--write")
    assert code == 2
    assert payload["error"]["code"] == "GUI_SUPPORT_ERROR"
    assert (project / GUI_SUPPORT_ASSET_PATH).read_text(encoding="utf-8") == GUI_SUPPORT_SOURCE


def test_existing_different_target_is_never_overwritten(tmp_path):
    project = unity_project(tmp_path)
    target = project / GUI_SUPPORT_ASSET_PATH
    target.parent.mkdir(parents=True)
    original = "// user-owned GUI\n"
    target.write_text(original, encoding="utf-8")
    state = inspect_gui_support(project)
    assert state["provider"] == "target_conflict"
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
    with pytest.raises(ValueError, match="escapes through a symbolic link"):
        install_gui_support(project, write=True)
    assert outside.read_text(encoding="utf-8") == "// outside\n"


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
    assert target.read_text(encoding="utf-8") == "// changed by project\n"


def test_project_shape_is_validated_before_any_write(tmp_path):
    project = tmp_path / "NotUnity"
    project.mkdir()
    code, payload = run_cli("gui-support", str(project), "--write")
    assert code == 2
    assert payload["error"]["code"] == "GUI_SUPPORT_ERROR"
    assert not (project / "Assets").exists()
