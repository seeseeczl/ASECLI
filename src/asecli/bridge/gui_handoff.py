"""Recoverable fallback-to-native MZGUI provider handoff."""

from __future__ import annotations

import hashlib
from pathlib import Path

from ._gui_handoff_store import (
    disable_known_fallback,
    handoff_backup_path,
    remove_known_resource,
    restore_known_fallback,
)
from ._gui_project import unity_project
from ._gui_resource_store import install_gui_resource
from .gui_support import (
    GUI_SUPPORT_ASSET_PATH,
    GUI_SUPPORT_KNOWN_PREVIOUS,
    GUI_SUPPORT_RESOURCE_PARTS,
    GUI_SUPPORT_SHA256,
    inspect_gui_support,
)
from .resource_text import compose_resource_text


GUI_AUTHORING_RESOURCE_PARTS = GUI_SUPPORT_RESOURCE_PARTS[2:]
GUI_AUTHORING_SOURCE = compose_resource_text(
    "asecli.bridge", "resources", GUI_AUTHORING_RESOURCE_PARTS
)
GUI_AUTHORING_SHA256 = hashlib.sha256(GUI_AUTHORING_SOURCE.encode("utf-8")).hexdigest()


def handoff_gui_support(
    project_root: str | Path,
    *,
    write: bool = False,
    runtime_probe: dict | None = None,
) -> dict:
    """Install the authoring-only bridge, then verify native takeover or roll back."""
    project = unity_project(project_root, GUI_SUPPORT_ASSET_PATH)
    state = inspect_gui_support(project_root, runtime_probe=runtime_probe)
    target_digest = state["asecli_material_gui"]["actual_sha256"]
    known = {GUI_SUPPORT_SHA256, *GUI_SUPPORT_KNOWN_PREVIOUS.keys()}

    pending = sorted(project.target.parent.glob(project.target.name + ".asecli-handoff-*.disabled"))
    if pending:
        return _finish_pending(
            project, state, pending, known, runtime_probe=runtime_probe, write=write
        )

    runtime = state["native_mzgui"]["runtime_providers"]
    native = [item for item in runtime if item["shader_gui"] and not item["fallback"]]
    fallback = [item for item in runtime if item["fallback"]]
    if (
        state["provider"] != "multiple"
        or target_digest not in known
        or runtime_probe is None
        or not runtime_probe.get("native_authoring_capable")
        or len(runtime) != 2
        or len(native) != 1
        or len(fallback) != 1
    ):
        raise RuntimeError("native handoff requires exactly a native provider plus one known fallback")
    backup = handoff_backup_path(project.target, target_digest)
    result = {**state, "action": "prepare_native_handoff", "handoff_backup": str(backup)}
    if not write:
        return result
    disable_known_fallback(project, target_digest, known)
    try:
        install_gui_resource(project, GUI_AUTHORING_SOURCE.encode("utf-8"))
    except BaseException:
        restore_known_fallback(project, backup, target_digest, known)
        raise
    return {
        **result,
        "action": "native_handoff_pending_verification",
        "written": True,
        "requires_editor_recompile": True,
    }


def _finish_pending(project, state, pending, known, *, runtime_probe, write):
    if len(pending) != 1 or project.target.is_symlink() or not project.target.is_file():
        raise RuntimeError("GUI handoff state is ambiguous; refusing automatic recovery")
    if hashlib.sha256(project.target.read_bytes()).hexdigest() != GUI_AUTHORING_SHA256:
        raise RuntimeError("GUI handoff authoring bridge changed; refusing automatic recovery")
    backup = pending[0]
    if backup.is_symlink() or not backup.is_file():
        raise RuntimeError("GUI handoff backup is not a regular file; refusing automatic recovery")
    digest = hashlib.sha256(backup.read_bytes()).hexdigest()
    if digest not in known or backup != handoff_backup_path(project.target, digest):
        raise RuntimeError("GUI handoff backup is unknown; refusing automatic recovery")
    runtime = state["native_mzgui"]["runtime_providers"]
    if (
        runtime_probe is not None
        and state["provider"] == "native_mzgui"
        and len(runtime) == 1
        and runtime[0]["shader_gui"]
        and not runtime[0]["fallback"]
    ):
        return {**state, "action": "native_handoff_verified", "handoff_backup": str(backup)}
    result = {**state, "action": "rollback_native_handoff", "handoff_backup": str(backup)}
    if write:
        remove_known_resource(project, project.target, GUI_AUTHORING_SHA256)
        restore_known_fallback(project, backup, digest, known)
        result.update(action="native_handoff_rolled_back", written=True)
    return result
