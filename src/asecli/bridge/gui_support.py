"""Inspect and install ASECLI's clean-room Unity material GUI."""

from __future__ import annotations

import hashlib
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
from .resource_text import compose_resource_text

GUI_SUPPORT_ASSET_PATH = "Assets/Editor/ASECLI/ASECLIMaterialGUI.cs"
GUI_SUPPORT_RESOURCE_PARTS = (
    "asecli_material_gui.part00.cs.txt",
    "asecli_material_gui.part01.cs.txt",
    "asecli_material_gui.authoring.part00.cs.txt",
    "asecli_material_gui.authoring.part01.cs.txt",
    "asecli_material_gui.reconciliation.cs.txt",
    "asecli_material_gui.transaction.cs.txt",
    "asecli_material_gui.hydration.cs.txt",
)
GUI_SUPPORT_SOURCE = compose_resource_text(
    "asecli.bridge", "resources", GUI_SUPPORT_RESOURCE_PARTS
)
GUI_SUPPORT_SHA256 = hashlib.sha256(GUI_SUPPORT_SOURCE.encode("utf-8")).hexdigest()
GUI_SUPPORT_KNOWN_PREVIOUS = {
    "cf45c7d6ad6aa79880205d73f7a6db45e20239cb312f91743056c5efa00b41b8": "0.2.0-original",
    "9541c541628b8404c66ca2c36e80af25f69960d6e1a07deabad53fd6233c5b7a": "0.3.1-material-only",
    "76a092825c44ea43fa10bde7cd4185c3af1d3c26a900d90da2d8fadde150967f": "0.3.1-authoring-preview",
    "738a79e7e9198dd6b21879d7d42dfad4dae6b74ef6e50e7cf17c4b3372d0e92c": "0.3.2-portable-mzgui",
    "77ccadf84e3c2c1eddff343ae535c09af15402b92172e772efdf481d06c3433e": "0.3.1-authoring-preview",
}
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
    target_state, actual_sha256 = _target_state(project.target)
    providers = []
    if native_evidence:
        providers.append("native_mzgui")
    if target_state in {"installed", "upgrade_available"}:
        providers.append("asecli_compat")
    runtime_fallback = [item for item in runtime_provider_details if item["fallback"]]
    runtime_conflict = len(runtime_provider_details) > 1
    if runtime_conflict:
        provider = "multiple"
        recommended_editor = None
    elif native_evidence:
        provider = "multiple" if target_state in {"installed", "upgrade_available"} else "native_mzgui"
        recommended_editor = MZGUI_EDITOR if provider == "native_mzgui" else None
    elif runtime_fallback and target_state == "absent":
        provider = "fallback_external"
        recommended_editor = MZGUI_EDITOR
    elif target_state == "conflict":
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
        "would_write": provider in {"missing", "asecli_upgrade_available"},
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
        state["action"] = "use_native_mzgui"
        state["would_write"] = False
        return state
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


def _target_state(target: Path) -> tuple[str, str | None]:
    if target.is_symlink():
        return "conflict", None
    if not target.exists():
        return "absent", None
    if not target.is_file():
        return "conflict", None
    actual = hashlib.sha256(target.read_bytes()).hexdigest()
    if actual == GUI_SUPPORT_SHA256:
        return "installed", actual
    if actual in GUI_SUPPORT_KNOWN_PREVIOUS:
        return "upgrade_available", actual
    return "conflict", actual
