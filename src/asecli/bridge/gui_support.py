"""Inspect and install ASECLI's clean-room Unity material GUI."""

from __future__ import annotations

import os
from pathlib import Path

from ..core import ASECLI_GUI_EDITOR, MZGUI_EDITOR
from ._gui_project import unity_project
from ._gui_resource_store import install_gui_resource
from ._gui_resource_upgrade import upgrade_backup_path, upgrade_gui_resource
from .gui_provider_detection import (
    runtime_providers,
    scan_native_mzgui,
    validate_runtime_probe,
)
from .gui_presentation import inspect_inline_help_presentation, require_inline_help_presentation
from .gui_support_resource import (
    GUI_AUTHORING_SHA256,
    GUI_AUTHORING_SOURCE,
    GUI_SUPPORT_ASSET_PATH,
    GUI_SUPPORT_KNOWN_PREVIOUS,
    GUI_SUPPORT_RESOURCE_PARTS,
    GUI_SUPPORT_SHA256,
    GUI_SUPPORT_SOURCE,
    gui_target_state,
)


def inspect_gui_support(
    project_root: str | Path, *, runtime_probe: dict | None = None
) -> dict:
    """Prefer native MZGUI; otherwise select ASECLI's Editor fallback."""
    project = unity_project(project_root, GUI_SUPPORT_ASSET_PATH)
    native_evidence, native_candidates = scan_native_mzgui(
        project.root, skip_source_name=Path(GUI_SUPPORT_ASSET_PATH).name
    )
    runtime_provider_details: list[dict] = []
    if runtime_probe is not None:
        validate_runtime_probe(runtime_probe, project.assets)
        runtime_provider_details = runtime_providers(runtime_probe)
        runtime_native = [
            item
            for item in runtime_provider_details
            if item["shader_gui"] and not item["fallback"]
        ]
        if len(runtime_provider_details) == 1 and runtime_native:
            native_evidence = [
                *native_evidence,
                "runtime:" + runtime_native[0]["assembly"],
            ]
        elif not runtime_provider_details and native_evidence:
            native_candidates = [*native_candidates, *native_evidence]
            native_evidence = []
    target_state, actual_sha256 = gui_target_state(project.target)
    providers = []
    if native_evidence:
        providers.append("native_mzgui")
    if target_state in {"installed", "upgrade_available"}:
        providers.append("asecli_compat")
    elif target_state == "native_extension":
        providers.append("asecli_authoring_extension")
    runtime_fallback = [item for item in runtime_provider_details if item["fallback"]]
    runtime_conflict = len(runtime_provider_details) > 1
    if runtime_conflict:
        provider = "multiple"
        recommended_editor = None
    elif native_evidence:
        if target_state in {"installed", "upgrade_available"}:
            provider = "multiple"
            recommended_editor = None
        elif target_state == "conflict":
            provider = "target_conflict"
            recommended_editor = None
        else:
            provider = "native_mzgui"
            recommended_editor = MZGUI_EDITOR
    elif runtime_fallback and target_state == "absent":
        provider = "fallback_external"
        recommended_editor = MZGUI_EDITOR
    elif target_state in {"conflict", "native_extension"}:
        provider = "target_conflict"
        recommended_editor = None
    elif native_candidates:
        provider = "unknown"
        recommended_editor = None
    elif target_state == "installed":
        provider = "asecli_compat"
        recommended_editor = MZGUI_EDITOR
    elif target_state == "upgrade_available":
        provider = "asecli_upgrade_available"
        recommended_editor = MZGUI_EDITOR
    else:
        provider = "missing"
        recommended_editor = MZGUI_EDITOR
    upgrade_from = GUI_SUPPORT_KNOWN_PREVIOUS.get(actual_sha256)
    backup = (
        upgrade_backup_path(project.target, actual_sha256, GUI_SUPPORT_KNOWN_PREVIOUS)
        if upgrade_from
        else None
    )

    return {
        "project_root": str(project.root),
        "provider": provider,
        "providers": providers,
        "recommended_editor": recommended_editor,
        "native_mzgui": {
            "detected": bool(native_evidence),
            "status": "detected" if native_evidence else ("unknown" if native_candidates else "not_detected"),
            "editor": MZGUI_EDITOR,
            "evidence": sorted(set(native_evidence)),
            "candidates": sorted(set(native_candidates)),
            "runtime_probe": runtime_probe,
            "runtime_providers": runtime_provider_details,
        },
        "asecli_material_gui": {
            "editor": MZGUI_EDITOR,
            "legacy_editor_alias": ASECLI_GUI_EDITOR,
            "target": str(project.target),
            "asset_path": GUI_SUPPORT_ASSET_PATH,
            "state": target_state,
            "expected_sha256": GUI_SUPPORT_SHA256,
            "actual_sha256": actual_sha256,
            "upgrade_available": upgrade_from is not None,
            "upgrade_from": upgrade_from,
            "backup": str(backup) if backup else None,
        },
        "capabilities": {
            "foldout": "FoldoutMzgui",
            "tooltip": "TooltipMzgui",
            "help_box": "HelpBoxMzgui",
            "enabled_if": "EnableIfMzgui",
            "inline_help_presentation": inspect_inline_help_presentation(GUI_SUPPORT_SOURCE),
            "fallback_editor": MZGUI_EDITOR,
            "legacy_fallback_editor": ASECLI_GUI_EDITOR,
            "authoring": {
                "surface": "Window/Amplify Shader Editor/MZGUI Attributes (ASECLI)",
                "storage": "ase_custom_attributes",
                "version_strategy": "runtime_capability_probe",
                "patches_ase_source": False,
            },
            "automatic_technical_tooltip": ["property_name", "shader_default_value"],
            "ase_version_dependency": False,
        },
        "would_write": provider in {"missing", "asecli_upgrade_available"}
        or (provider == "native_mzgui" and target_state == "absent"),
        "written": False,
    }


def install_gui_support(
    project_root: str | Path,
    *,
    write: bool = False,
    runtime_probe: dict | None = None,
) -> dict:
    """Inject the Editor fallback only after native MZGUI was ruled out."""
    state = inspect_gui_support(project_root, runtime_probe=runtime_probe)
    if state["provider"] == "multiple":
        raise RuntimeError(
            "native MZGUI and ASECLI fallback are both installed; remove the ASECLI fallback "
            "before selecting MZGUI.MZGUI"
        )
    if state["provider"] == "native_mzgui":
        target_state = state["asecli_material_gui"]["state"]
        if target_state == "native_extension":
            state["action"] = "use_native_mzgui"
            state["would_write"] = False
            return state
        state["action"] = "install_native_mzgui_extension"
        if not write:
            return state
        project = unity_project(project_root, GUI_SUPPORT_ASSET_PATH)
        install_gui_resource(project, GUI_AUTHORING_SOURCE.encode("utf-8"))
        installed = inspect_gui_support(project_root, runtime_probe=runtime_probe)
        if installed["provider"] != "native_mzgui" or installed[
            "asecli_material_gui"
        ]["state"] != "native_extension":
            raise RuntimeError("ASECLI native MZGUI extension failed digest verification")
        installed.update(
            action="install_native_mzgui_extension",
            would_write=False,
            written=True,
            requires_editor_recompile=True,
        )
        return installed
    if state["provider"] == "fallback_external":
        state["action"] = "use_external_fallback"
        state["would_write"] = False
        return state
    if state["provider"] == "unknown":
        raise RuntimeError(
            "native MZGUI may exist in an unverified source or assembly; run gui-support "
            "with --runtime-probe while the target Editor is connected before installing"
        )
    if write:
        require_inline_help_presentation(GUI_SUPPORT_SOURCE)
    target_state = state["asecli_material_gui"]["state"]
    if target_state == "conflict":
        raise FileExistsError(
            "ASECLI GUI support target already exists with different content; refusing to overwrite: "
            + state["asecli_material_gui"]["target"]
        )
    if target_state == "installed":
        state["action"] = "already_installed"
        state["would_write"] = False
        return state

    upgrading = target_state == "upgrade_available"
    state["action"] = (
        "upgrade_asecli_material_gui" if upgrading else "install_asecli_material_gui"
    )
    if not write:
        return state

    project = unity_project(project_root, GUI_SUPPORT_ASSET_PATH)
    backup_path = None
    if upgrading:
        backup_path = upgrade_gui_resource(
            project,
            GUI_SUPPORT_SOURCE.encode("utf-8"),
            state["asecli_material_gui"]["actual_sha256"],
            GUI_SUPPORT_KNOWN_PREVIOUS,
        )
    else:
        install_gui_resource(project, GUI_SUPPORT_SOURCE.encode("utf-8"))

    installed = inspect_gui_support(project_root, runtime_probe=runtime_probe)
    if installed["asecli_material_gui"]["state"] != "installed":
        raise RuntimeError("ASECLI GUI support was written but failed digest verification")
    installed["action"] = (
        "upgrade_asecli_material_gui" if upgrading else "install_asecli_material_gui"
    )
    installed["would_write"] = False
    installed["written"] = True
    installed["requires_editor_recompile"] = True
    installed["backed_up"] = backup_path is not None
    installed["backup"] = str(backup_path) if backup_path else None
    return installed
