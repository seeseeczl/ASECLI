"""Choose the single material-GUI provider for an Editor create operation."""

from pathlib import Path

from ..bridge import MZGUI_EDITOR, install_gui_support


def select_editor_provider(shader_path: str) -> tuple[str, dict | None]:
    """Install the fallback only when the enclosing Unity project lacks MZGUI.

    Projectless behavior exists solely for isolated bridge test doubles; a real
    Editor create target must be inside a Unity project.
    """
    project_root = unity_project_root(Path(shader_path).resolve())
    if project_root is None:
        return MZGUI_EDITOR, None
    support = install_gui_support(project_root, write=True)
    editor = support.get("recommended_editor")
    if not isinstance(editor, str):
        raise RuntimeError("material GUI provider selection did not return an editor")
    return editor, support


def unity_project_root(path: Path) -> Path | None:
    current = path.parent
    while current != current.parent:
        if (current / "Assets").is_dir() and (current / "ProjectSettings").is_dir():
            return current
        current = current.parent
    return None
