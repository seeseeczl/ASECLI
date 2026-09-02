"""Inspect and install ASECLI's clean-room Unity material GUI."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
from importlib import resources
import os
from pathlib import Path
import stat

from ..core.custom_gui import ASECLI_GUI_EDITOR

GUI_SUPPORT_ASSET_PATH = "Assets/Editor/ASECLI/ASECLIMaterialGUI.cs"
GUI_SUPPORT_SOURCE = (
    resources.files("asecli.bridge")
    .joinpath("resources/asecli_material_gui.cs.txt")
    .read_text(encoding="utf-8")
)
GUI_SUPPORT_SHA256 = hashlib.sha256(GUI_SUPPORT_SOURCE.encode("utf-8")).hexdigest()
_SECURE_DIRECTORY_OPERATIONS_AVAILABLE = (
    os.open in os.supports_dir_fd
    and os.mkdir in os.supports_dir_fd
    and hasattr(os, "O_NOFOLLOW")
)

@dataclass(frozen=True)
class UnityProject:
    root: Path
    assets: Path
    target: Path


def inspect_gui_support(project_root: str | Path) -> dict:
    """Inspect the fixed ASECLI material-GUI resource without changing the project."""
    project = _unity_project(project_root)
    target_state, actual_sha256 = _target_state(project.target)
    provider = "target_conflict" if target_state == "conflict" else (
        "asecli_compat" if target_state == "installed" else "missing"
    )
    recommended_editor = None if target_state == "conflict" else ASECLI_GUI_EDITOR

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
        },
        "capabilities": {
            "foldout": "ASECLIFoldout",
            "tooltip": "ASECLITooltip",
            "help_box": "ASECLIHelpBox",
            "legacy_read_compatibility": ["FoldoutMzgui", "TooltipMzgui", "HelpBoxMzgui"],
            "automatic_technical_tooltip": ["property_name", "shader_default_value"],
            "ase_version_dependency": False,
        },
        "would_write": provider == "missing",
        "written": False,
    }


def install_gui_support(
    project_root: str | Path,
    *,
    write: bool = False,
) -> dict:
    """Plan or install the fixed resource without overwriting user files."""
    state = inspect_gui_support(project_root)
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

    state["action"] = "install_asecli_material_gui"
    if not write:
        return state

    _install_gui_resource(_unity_project(project_root))

    installed = inspect_gui_support(project_root)
    if installed["asecli_material_gui"]["state"] != "installed":
        raise RuntimeError("ASECLI GUI support was written but failed digest verification")
    installed["action"] = "install_asecli_material_gui"
    installed["would_write"] = False
    installed["written"] = True
    installed["requires_editor_recompile"] = True
    return installed


def _install_gui_resource(project: UnityProject) -> None:
    """Create the resource through verified directory descriptors only."""
    _require_secure_directory_operations()
    descriptors: list[int] = []
    try:
        root_descriptor = _open_directory(project.root)
        descriptors.append(root_descriptor)
        assets_descriptor = _open_directory_at(root_descriptor, "Assets")
        descriptors.append(assets_descriptor)
        editor_descriptor = _open_or_create_directory(assets_descriptor, "Editor")
        descriptors.append(editor_descriptor)
        support_descriptor = _open_or_create_directory(editor_descriptor, "ASECLI")
        descriptors.append(support_descriptor)
        _create_gui_resource(support_descriptor, project.target)
        os.fsync(support_descriptor)
    finally:
        for descriptor in reversed(descriptors):
            os.close(descriptor)


def _require_secure_directory_operations() -> None:
    if not _SECURE_DIRECTORY_OPERATIONS_AVAILABLE:
        raise RuntimeError(
            "secure ASECLI GUI installation requires dir_fd and O_NOFOLLOW support on this platform"
        )


def _directory_flags() -> int:
    return (
        os.O_RDONLY
        | getattr(os, "O_DIRECTORY", 0)
        | getattr(os, "O_CLOEXEC", 0)
        | os.O_NOFOLLOW
    )


def _open_directory(path: Path) -> int:
    descriptor = os.open(path, _directory_flags())
    _require_directory(descriptor, path)
    return descriptor


def _open_directory_at(parent_descriptor: int, name: str) -> int:
    descriptor = os.open(name, _directory_flags(), dir_fd=parent_descriptor)
    _require_directory(descriptor, Path(name))
    return descriptor


def _open_or_create_directory(parent_descriptor: int, name: str) -> int:
    try:
        return _open_directory_at(parent_descriptor, name)
    except FileNotFoundError:
        try:
            os.mkdir(name, mode=0o755, dir_fd=parent_descriptor)
        except FileExistsError:
            pass
        return _open_directory_at(parent_descriptor, name)


def _require_directory(descriptor: int, path: Path) -> None:
    if stat.S_ISDIR(os.fstat(descriptor).st_mode):
        return
    os.close(descriptor)
    raise NotADirectoryError(f"ASECLI GUI support directory is not a directory: {path}")


def _create_gui_resource(parent_descriptor: int, target: Path) -> None:
    flags = (
        os.O_WRONLY
        | os.O_CREAT
        | os.O_EXCL
        | getattr(os, "O_CLOEXEC", 0)
        | os.O_NOFOLLOW
    )
    try:
        descriptor = os.open(target.name, flags, 0o644, dir_fd=parent_descriptor)
    except FileExistsError as exc:
        raise FileExistsError(
            f"ASECLI GUI support target appeared during installation; refusing to overwrite: {target}"
        ) from exc
    except FileNotFoundError as exc:
        raise RuntimeError(
            f"ASECLI GUI support directory changed during installation; refusing to write: {target}"
        ) from exc
    opened_stat = os.fstat(descriptor)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="") as handle:
            handle.write(GUI_SUPPORT_SOURCE)
            handle.flush()
            os.fsync(handle.fileno())
    except BaseException:
        _unlink_created_resource(parent_descriptor, target.name, opened_stat)
        raise


def _unlink_created_resource(parent_descriptor: int, name: str, opened_stat: os.stat_result) -> None:
    try:
        current_stat = os.stat(name, dir_fd=parent_descriptor, follow_symlinks=False)
        if (current_stat.st_dev, current_stat.st_ino) == (opened_stat.st_dev, opened_stat.st_ino):
            os.unlink(name, dir_fd=parent_descriptor)
    except FileNotFoundError:
        pass


def _unity_project(project_root: str | Path) -> UnityProject:
    root = Path(project_root).expanduser().resolve()
    if not root.is_dir():
        raise FileNotFoundError(f"Unity project root not found: {root}")
    assets = root / "Assets"
    settings = root / "ProjectSettings"
    if not assets.is_dir() or not settings.is_dir():
        raise ValueError("project root must contain Assets and ProjectSettings directories")
    _assert_inside_project(assets, root)
    target = root / GUI_SUPPORT_ASSET_PATH
    _assert_inside_project(target, root)
    return UnityProject(root=root, assets=assets, target=target)


def _assert_inside_project(path: Path, project_root: Path) -> None:
    resolved = path.resolve(strict=False)
    try:
        resolved.relative_to(project_root)
    except ValueError as exc:
        raise ValueError(f"project path escapes through a symbolic link: {path}") from exc


def _target_state(target: Path) -> tuple[str, str | None]:
    if target.is_symlink():
        return "conflict", None
    if not target.exists():
        return "absent", None
    if not target.is_file():
        return "conflict", None
    actual = hashlib.sha256(target.read_bytes()).hexdigest()
    return ("installed" if actual == GUI_SUPPORT_SHA256 else "conflict"), actual
