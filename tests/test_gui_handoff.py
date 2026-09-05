"""REG-0047: runtime provider discovery and reversible native handoff."""

from pathlib import Path

from asecli.bridge.gui_handoff import handoff_gui_support
from asecli.bridge.gui_support import (
    GUI_SUPPORT_ASSET_PATH,
    GUI_SUPPORT_SOURCE,
    inspect_gui_support,
    install_gui_support,
)


def unity_project(tmp_path: Path) -> Path:
    project = tmp_path / "UnityProject"
    (project / "Assets").mkdir(parents=True)
    (project / "ProjectSettings").mkdir()
    return project


def probe(project: Path, providers: list[dict], capable: bool = True) -> dict:
    return {
        "protocol": "ASECLI_GUI_SUPPORT_PROBE_V2",
        "native_authoring_capable": capable,
        "assets_path": str((project / "Assets").resolve()),
        "type_found": bool(providers),
        "detected": len(providers) == 1 and not providers[0]["fallback"],
        "fallback": len(providers) == 1 and providers[0]["fallback"],
        "assembly": providers[0]["assembly"] if len(providers) == 1 else None,
        "providers": providers,
    }


NATIVE = {"full_name": "MZGUI.MZGUI", "assembly": "Native", "shader_gui": True, "fallback": False}
FALLBACK = {"full_name": "MZGUI.MZGUI", "assembly": "Fallback", "shader_gui": True, "fallback": True}


def add_native(project: Path) -> None:
    source = project / "Assets/MZGUI/MZGUI.cs"
    source.parent.mkdir(parents=True)
    source.write_text("using UnityEditor; namespace MZGUI { class MZGUI : ShaderGUI {} }", encoding="utf-8")


def test_external_fallback_is_used_without_writing_the_fixed_target(tmp_path):
    project = unity_project(tmp_path)
    external = {**FALLBACK, "assembly": "External.Fallback.Editor"}
    state = install_gui_support(project, write=True, runtime_probe=probe(project, [external], False))
    assert state["provider"] == "fallback_external"
    assert state["action"] == "use_external_fallback"
    assert state["would_write"] is False
    assert not (project / GUI_SUPPORT_ASSET_PATH).exists()


def test_runtime_probe_reports_all_same_name_providers_as_conflict(tmp_path):
    project = unity_project(tmp_path)
    providers = [NATIVE, FALLBACK]
    state = inspect_gui_support(project, runtime_probe=probe(project, providers))
    assert state["provider"] == "multiple"
    assert state["recommended_editor"] is None
    assert state["would_write"] is False
    assert state["native_mzgui"]["runtime_providers"] == providers


def test_native_handoff_is_dry_run_reversible_and_runtime_verified(tmp_path):
    project = unity_project(tmp_path)
    install_gui_support(project, write=True)
    add_native(project)
    conflict = probe(project, [NATIVE, FALLBACK])
    planned = handoff_gui_support(project, runtime_probe=conflict)
    target = project / GUI_SUPPORT_ASSET_PATH
    assert planned["action"] == "prepare_native_handoff"
    assert target.exists()

    pending = handoff_gui_support(project, write=True, runtime_probe=conflict)
    backup = Path(pending["handoff_backup"])
    assert pending["action"] == "native_handoff_pending_verification"
    assert target.exists() and backup.exists()
    assert target.read_text(encoding="utf-8") != GUI_SUPPORT_SOURCE

    verified = handoff_gui_support(project, runtime_probe=probe(project, [NATIVE]))
    assert verified["action"] == "native_handoff_verified"
    assert backup.exists()


def test_failed_native_handoff_verification_restores_fallback(tmp_path):
    project = unity_project(tmp_path)
    install_gui_support(project, write=True)
    add_native(project)
    pending = handoff_gui_support(
        project, write=True, runtime_probe=probe(project, [NATIVE, FALLBACK])
    )
    rolled_back = handoff_gui_support(
        project, write=True, runtime_probe=probe(project, [], False)
    )
    assert rolled_back["action"] == "native_handoff_rolled_back"
    assert (project / GUI_SUPPORT_ASSET_PATH).read_text(encoding="utf-8") == GUI_SUPPORT_SOURCE
    assert not Path(pending["handoff_backup"]).exists()
