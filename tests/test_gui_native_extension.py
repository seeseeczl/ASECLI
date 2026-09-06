"""Native MZGUI keeps its provider while ASECLI adds portable authoring support."""

from pathlib import Path

from asecli.bridge.gui_support import (
    GUI_AUTHORING_SOURCE,
    GUI_SUPPORT_ASSET_PATH,
    install_gui_support,
)
from asecli.core import MZGUI_EDITOR


def unity_project(tmp_path: Path) -> Path:
    project = tmp_path / "UnityProject"
    (project / "Assets/Legacy").mkdir(parents=True)
    (project / "ProjectSettings").mkdir()
    (project / "Assets/Legacy/MZGUI.cs").write_text(
        "using UnityEditor; namespace MZGUI { class MZGUI : ShaderGUI {} }",
        encoding="utf-8",
    )
    return project


def test_native_mzgui_gets_authoring_and_condition_extension_without_second_provider(tmp_path):
    project = unity_project(tmp_path)

    installed = install_gui_support(project, write=True)

    assert installed["provider"] == "native_mzgui"
    assert installed["recommended_editor"] == MZGUI_EDITOR
    assert installed["action"] == "install_native_mzgui_extension"
    target = project / GUI_SUPPORT_ASSET_PATH
    assert target.read_text(encoding="utf-8") == GUI_AUTHORING_SOURCE
    assert "class EnableIfMzguiDrawer : MZGUI.MzguiDrawer" in GUI_AUTHORING_SOURCE
    assert "class MZGUI :" not in GUI_AUTHORING_SOURCE

    repeated = install_gui_support(project, write=True)
    assert repeated["action"] == "use_native_mzgui"
    assert repeated["written"] is False
