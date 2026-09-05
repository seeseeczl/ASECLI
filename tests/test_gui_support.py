"""REG-0030/REG-0035: ASECLI material GUI installation contract."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

from asecli.bridge.gui_support import (
    GUI_SUPPORT_ASSET_PATH,
    GUI_SUPPORT_RESOURCE_PARTS,
    GUI_SUPPORT_SHA256,
    GUI_SUPPORT_SOURCE,
    inspect_gui_support,
    install_gui_support,
)
from asecli.core import ASECLI_GUI_EDITOR, MZGUI_EDITOR


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


def test_packaged_source_reads_the_mzgui_protocol_for_the_fallback_editor():
    assert "class ASECLIMaterialGUI : ShaderGUI, IASECLIFallbackProvider" in GUI_SUPPORT_SOURCE
    assert "namespace MZGUI" in GUI_SUPPORT_SOURCE
    assert "class MZGUI : ASECLI.MaterialGUI.ASECLIMaterialGUI" in GUI_SUPPORT_SOURCE
    assert "class ASECLIFoldoutDecorator" in GUI_SUPPORT_SOURCE
    assert "class ASECLITooltipDecorator" in GUI_SUPPORT_SOURCE
    assert "class ASECLIHelpBoxDecorator" in GUI_SUPPORT_SOURCE
    assert "class FoldoutMzguiDecorator" in GUI_SUPPORT_SOURCE
    assert "class TooltipMzguiDecorator" in GUI_SUPPORT_SOURCE
    assert "class HelpBoxMzguiDecorator" in GUI_SUPPORT_SOURCE
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
    assert "using AmplifyShaderEditor" not in GUI_SUPPORT_SOURCE
    assert "typeof(AmplifyShaderEditor" not in GUI_SUPPORT_SOURCE


def test_packaged_fallback_adds_visual_ase_authoring_without_patching_ase_source():
    assert 'MenuItem("Window/Amplify Shader Editor/MZGUI Attributes (ASECLI)")' in GUI_SUPPORT_SOURCE
    assert 'new GUIContent("MZGUI Attributes")' in GUI_SUPPORT_SOURCE
    assert '"使用 MZGUI.MZGUI 材质面板"' in GUI_SUPPORT_SOURCE
    assert 'ToggleLeft("Foldout"' in GUI_SUPPORT_SOURCE
    assert 'ToggleLeft("Tooltip"' in GUI_SUPPORT_SOURCE
    assert 'ToggleLeft("HelpBox"' in GUI_SUPPORT_SOURCE
    assert '"m_customAttr", "m_customAttributes"' in GUI_SUPPORT_SOURCE
    assert "runtime capability" not in GUI_SUPPORT_SOURCE  # no optimistic version whitelist
    assert "当前 ASE 版本未暴露兼容的 Custom Attributes 存储；已停止写入" in GUI_SUPPORT_SOURCE
    assert "class ASEMetadataHydrator" in GUI_SUPPORT_SOURCE
    assert "TryMergeRaw" in GUI_SUPPORT_SOURCE
    assert "class ASEApplyTransaction" in GUI_SUPPORT_SOURCE
    assert 'string stage = "write_attributes"' in GUI_SUPPORT_SOURCE
    assert "Undo.RevertAllDownToGroup(group)" in GUI_SUPPORT_SOURCE
    assert 'rollback=" + (restoredAttributes && restoredMaster && restoredDisk ? "ok" : "failed")' in GUI_SUPPORT_SOURCE
    assert "class ASENativeMzguiReconciler" in GUI_SUPPORT_SOURCE
    assert '"m_mzguiAttribs"' in GUI_SUPPORT_SOURCE
    assert '"m_selectedMzguiAttribs"' in GUI_SUPPORT_SOURCE
    assert '"ASECLIFoldout"' in GUI_SUPPORT_SOURCE
    assert '"ASECLITooltip"' in GUI_SUPPORT_SOURCE
    assert '"ASECLIHelpBox"' in GUI_SUPPORT_SOURCE
    assert "同一 MZGUI 属性存在冲突的 canonical 值；已停止写入" in GUI_SUPPORT_SOURCE
    assert "patch PropertyNode" not in GUI_SUPPORT_SOURCE


def test_gui_resource_fragments_are_bounded_and_compose_byte_stably():
    resources = ROOT / "src/asecli/bridge/resources"
    parts = [resources / name for name in GUI_SUPPORT_RESOURCE_PARTS]
    assert all(path.is_file() for path in parts)
    assert all(len(path.read_text(encoding="utf-8").splitlines()) <= 300 for path in parts)
    assert "".join(path.read_text(encoding="utf-8") for path in parts) == GUI_SUPPORT_SOURCE
    assert hashlib.sha256(GUI_SUPPORT_SOURCE.encode("utf-8")).hexdigest() == (
        "e0fa59a9fa3ca2840f8ee2d76e03fbbb862919d2476aefec0fe7f4e64150f034"
    )


def test_packaged_source_draws_lightweight_inline_help_style():
    assert "DrawInlineHelp(metadata.Help)" in GUI_SUPPORT_SOURCE
    assert "EditorGUILayout.HelpBox(metadata.Help, MessageType.Info)" not in GUI_SUPPORT_SOURCE
    assert "new GUIStyle(EditorStyles.miniLabel)" in GUI_SUPPORT_SOURCE
    assert "style.fontStyle = FontStyle.Italic" in GUI_SUPPORT_SOURCE
    assert "style.wordWrap = true" in GUI_SUPPORT_SOURCE
    assert "Rect accentRect" in GUI_SUPPORT_SOURCE
    assert "EditorGUI.DrawRect(backgroundRect" in GUI_SUPPORT_SOURCE
    assert "EditorGUI.DrawRect(accentRect" in GUI_SUPPORT_SOURCE


def test_packaged_source_wraps_long_property_labels_without_truncation():
    assert "ShouldWrapPropertyLabel" in GUI_SUPPORT_SOURCE
    assert "DrawWrappedProperty" in GUI_SUPPORT_SOURCE
    assert "wrappedLabel.wordWrap = true" in GUI_SUPPORT_SOURCE
    assert "materialEditor.ShaderProperty(position, property, GUIContent.none)" in GUI_SUPPORT_SOURCE


def test_packaged_source_formats_tooltip_defaults_without_float_noise():
    assert 'ToString("0.######", CultureInfo.InvariantCulture)' in GUI_SUPPORT_SOURCE
    assert 'ToString("G7", CultureInfo.InvariantCulture)' not in GUI_SUPPORT_SOURCE
    assert 'ToString("G9", CultureInfo.InvariantCulture)' not in GUI_SUPPORT_SOURCE


def test_inspection_reports_the_inline_help_presentation_contract(tmp_path):
    presentation = inspect_gui_support(unity_project(tmp_path))["capabilities"][
        "inline_help_presentation"
    ]
    assert presentation == {
        "contract": "asecli.inline-help.v1",
        "icon": "none",
        "border": "none",
        "background_rgba": [0.0, 0.0, 0.0, 0.1],
        "accent": {
            "edge": "left",
            "width": 3.0,
            "rgba": [1.0, 1.0, 1.0, 0.3],
        },
        "typography": {
            "base": "EditorStyles.miniLabel",
            "font_style": "italic",
            "dark_skin_alpha": 0.4,
            "light_skin_alpha": 0.55,
        },
        "layout": {"text_inset": [16.0, 4.0], "word_wrap": True},
        "valid": True,
        "violations": [],
    }


def test_install_refuses_a_packaged_gui_that_breaks_the_presentation_contract(
    tmp_path, monkeypatch
):
    project = unity_project(tmp_path)
    monkeypatch.setattr(
        "asecli.bridge.gui_support.GUI_SUPPORT_SOURCE",
        "EditorGUILayout.HelpBox(metadata.Help, MessageType.Info);",
    )
    planned = install_gui_support(project)
    assert planned["capabilities"]["inline_help_presentation"]["valid"] is False
    assert "forbidden:native_layout_help_box" in planned["capabilities"][
        "inline_help_presentation"
    ]["violations"]
    with pytest.raises(RuntimeError, match="inline-help presentation contract"):
        install_gui_support(project, write=True)
    assert not (project / GUI_SUPPORT_ASSET_PATH).exists()


def test_inspect_and_dry_run_do_not_create_project_files(tmp_path):
    project = unity_project(tmp_path)
    target = project / GUI_SUPPORT_ASSET_PATH
    state = inspect_gui_support(project)
    assert state["provider"] == "missing"
    assert state["recommended_editor"] == MZGUI_EDITOR
    assert state["asecli_material_gui"]["editor"] == MZGUI_EDITOR
    assert state["asecli_material_gui"]["legacy_editor_alias"] == ASECLI_GUI_EDITOR
    assert state["capabilities"]["foldout"] == "FoldoutMzgui"
    assert state["capabilities"]["tooltip"] == "TooltipMzgui"
    assert state["capabilities"]["help_box"] == "HelpBoxMzgui"
    assert state["capabilities"]["authoring"] == {
        "surface": "Window/Amplify Shader Editor/MZGUI Attributes (ASECLI)",
        "storage": "ase_custom_attributes",
        "version_strategy": "runtime_capability_probe",
        "patches_ase_source": False,
    }
    assert state["would_write"] is True
    planned = install_gui_support(project)
    assert planned["action"] == "install_asecli_material_gui"
    assert not target.exists()


def test_write_installs_exact_resource_and_is_idempotent(tmp_path):
    project = unity_project(tmp_path)
    target = project / GUI_SUPPORT_ASSET_PATH
    installed = install_gui_support(project, write=True)
    assert installed["provider"] == "asecli_compat"
    assert installed["recommended_editor"] == MZGUI_EDITOR
    assert installed["written"] is True
    assert installed["requires_editor_recompile"] is True
    assert target.read_text(encoding="utf-8") == GUI_SUPPORT_SOURCE
    assert installed["asecli_material_gui"]["actual_sha256"] == GUI_SUPPORT_SHA256

    repeated = install_gui_support(project, write=True)
    assert repeated["action"] == "already_installed"
    assert repeated["written"] is False


def test_runtime_probe_distinguishes_the_installed_fallback_from_native_mzgui(tmp_path):
    project = unity_project(tmp_path)
    install_gui_support(project, write=True)
    state = inspect_gui_support(
        project,
        runtime_probe={
            "protocol": "ASECLI_GUI_SUPPORT_PROBE_V1",
            "assets_path": str((project / "Assets").resolve()),
            "type_found": True,
            "detected": False,
            "fallback": True,
            "assembly": "Assembly-CSharp-Editor",
        },
    )

    assert state["provider"] == "asecli_compat"
    assert state["recommended_editor"] == MZGUI_EDITOR


def test_native_mzgui_is_selected_without_injecting_the_fallback(tmp_path):
    project = unity_project(tmp_path)
    native = project / "Assets/Legacy/MZGUI.cs"
    native.parent.mkdir(parents=True)
    native.write_text(
        "using UnityEditor; namespace MZGUI { class MZGUI : ShaderGUI {} }",
        encoding="utf-8",
    )

    installed = install_gui_support(project, write=True)
    assert installed["provider"] == "native_mzgui"
    assert installed["recommended_editor"] == MZGUI_EDITOR
    assert installed["action"] == "use_native_mzgui"
    assert not (project / GUI_SUPPORT_ASSET_PATH).exists()


def test_fallback_and_native_projects_share_the_same_public_editor_contract(tmp_path):
    fallback_project = unity_project(tmp_path / "fallback")
    native_project = unity_project(tmp_path / "native")
    native = native_project / "Assets/MZGUI/MZGUI.cs"
    native.parent.mkdir(parents=True)
    native.write_text(
        "using UnityEditor; namespace MZGUI { class MZGUI : ShaderGUI {} }",
        encoding="utf-8",
    )

    fallback = install_gui_support(fallback_project, write=True)
    native_state = install_gui_support(native_project, write=True)

    assert fallback["recommended_editor"] == MZGUI_EDITOR
    assert native_state["recommended_editor"] == MZGUI_EDITOR
    assert "namespace MZGUI" in (fallback_project / GUI_SUPPORT_ASSET_PATH).read_text(
        encoding="utf-8"
    )
    assert not (native_project / GUI_SUPPORT_ASSET_PATH).exists()


def test_unverified_mzgui_candidate_blocks_fallback_injection(tmp_path):
    project = unity_project(tmp_path)
    candidate = project / "Assets/Legacy/MZGUI.cs"
    candidate.parent.mkdir(parents=True)
    candidate.write_text("namespace MZGUI { class MZGUI {} }", encoding="utf-8")

    state = inspect_gui_support(project)
    assert state["provider"] == "unknown"
    with pytest.raises(RuntimeError, match="--runtime-probe"):
        install_gui_support(project, write=True)
    assert not (project / GUI_SUPPORT_ASSET_PATH).exists()


def test_native_and_fallback_providers_fail_closed_instead_of_competing(tmp_path):
    project = unity_project(tmp_path)
    install_gui_support(project, write=True)
    native = project / "Assets/Legacy/MZGUI.cs"
    native.parent.mkdir(parents=True)
    native.write_text(
        "using UnityEditor; namespace MZGUI { class MZGUI : ShaderGUI {} }",
        encoding="utf-8",
    )

    state = inspect_gui_support(project)
    assert state["provider"] == "multiple"
    assert state["recommended_editor"] is None
    with pytest.raises(RuntimeError, match="both installed"):
        install_gui_support(project, write=True)


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
    assert payload["data"]["capabilities"]["inline_help_presentation"]["valid"] is True
    assert (
        payload["data"]["capabilities"]["inline_help_presentation"]["contract"]
        == "asecli.inline-help.v1"
    )

    code, payload = run_cli("gui-support", str(project), "--write")
    assert code == 0
    assert payload["data"]["provider"] == "asecli_compat"
    assert payload["data"]["written"] is True

    target = project / GUI_SUPPORT_ASSET_PATH
    target.write_text("// changed by project\n", encoding="utf-8")
    code, payload = run_cli("gui-support", str(project), "--write")
    assert code == 2
    assert payload["error"]["code"] == "GUI_SUPPORT_ERROR"
