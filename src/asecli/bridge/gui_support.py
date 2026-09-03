"""Inspect and install ASECLI's clean-room Unity material GUI."""

from __future__ import annotations

import hashlib
import os
from pathlib import Path

from ..core import ASECLI_GUI_EDITOR
from ._gui_project import unity_project
from ._gui_resource_store import install_gui_resource
from ._gui_resource_upgrade import upgrade_backup_path, upgrade_gui_resource
from .gui_presentation import inspect_inline_help_presentation, require_inline_help_presentation
from .resource_text import compose_resource_text

GUI_SUPPORT_ASSET_PATH = "Assets/Editor/ASECLI/ASECLIMaterialGUI.cs"
GUI_SUPPORT_RESOURCE_PARTS = (
    "asecli_material_gui.part00.cs.txt",
    "asecli_material_gui.part01.cs.txt",
)
GUI_SUPPORT_SOURCE = compose_resource_text(
    "asecli.bridge", "resources", GUI_SUPPORT_RESOURCE_PARTS
)
GUI_SUPPORT_SHA256 = hashlib.sha256(GUI_SUPPORT_SOURCE.encode("utf-8")).hexdigest()
GUI_SUPPORT_KNOWN_PREVIOUS = {
    "cf45c7d6ad6aa79880205d73f7a6db45e20239cb312f91743056c5efa00b41b8": "0.2.0-original",
}
def inspect_gui_support(project_root: str | Path) -> dict:
    """Inspect the fixed ASECLI material-GUI resource without changing the project."""
    project = unity_project(project_root, GUI_SUPPORT_ASSET_PATH)
    target_state, actual_sha256 = _target_state(project.target)
    provider = {
        "conflict": "target_conflict",
        "installed": "asecli_compat",
        "upgrade_available": "asecli_upgrade_available",
        "absent": "missing",
    }[target_state]
    recommended_editor = None if target_state == "conflict" else ASECLI_GUI_EDITOR
    upgrade_from = GUI_SUPPORT_KNOWN_PREVIOUS.get(actual_sha256)
    backup = (
        upgrade_backup_path(project.target, actual_sha256, GUI_SUPPORT_KNOWN_PREVIOUS)
        if upgrade_from
        else None
    )

    return {
        "project_root": str(project.root),
        "provider": provider,
        "recommended_editor": recommended_editor,
        "asecli_material_gui": {
            "editor": ASECLI_GUI_EDITOR,
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
            "foldout": "ASECLIFoldout",
            "tooltip": "ASECLITooltip",
            "help_box": "ASECLIHelpBox",
            "inline_help_presentation": inspect_inline_help_presentation(GUI_SUPPORT_SOURCE),
            "legacy_read_compatibility": ["FoldoutMzgui", "TooltipMzgui", "HelpBoxMzgui"],
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
) -> dict:
    """Plan or install the fixed resource without overwriting user files."""
    state = inspect_gui_support(project_root)
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

    installed = inspect_gui_support(project_root)
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
