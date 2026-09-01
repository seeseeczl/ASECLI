"""Detect and install ASECLI's clean-room Unity material GUI compatibility layer."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
from importlib import resources
import os
from pathlib import Path
import re

from ..core.custom_gui import ASECLI_GUI_EDITOR, MZGUI_EDITOR

GUI_SUPPORT_ASSET_PATH = "Assets/Editor/ASECLI/ASECLIMaterialGUI.cs"
GUI_SUPPORT_SOURCE = (
    resources.files("asecli.bridge")
    .joinpath("resources/asecli_material_gui.cs.txt")
    .read_text(encoding="utf-8")
)
GUI_SUPPORT_SHA256 = hashlib.sha256(GUI_SUPPORT_SOURCE.encode("utf-8")).hexdigest()

_NATIVE_NAMESPACE_RE = re.compile(r"\bnamespace\s+MZGUI\b")
_NATIVE_GUI_RE = re.compile(r"\bclass\s+MZGUI\s*:\s*ShaderGUI\b")


@dataclass(frozen=True)
class UnityProject:
    root: Path
    assets: Path
    target: Path


def inspect_gui_support(project_root: str | Path) -> dict:
    """Inspect available material-GUI providers without changing the project."""
    project = _unity_project(project_root)
    native_evidence = _find_native_mzgui(project.root)
    target_state, actual_sha256 = _target_state(project.target)
    providers = []
    if native_evidence:
        providers.append("native_mzgui")
    if target_state == "installed":
        providers.append("asecli_compat")

    if native_evidence:
        provider = "native_mzgui" if target_state != "installed" else "multiple"
        recommended_editor = MZGUI_EDITOR if provider == "native_mzgui" else None
    elif target_state == "installed":
        provider = "asecli_compat"
        recommended_editor = ASECLI_GUI_EDITOR
    elif target_state == "conflict":
        provider = "target_conflict"
        recommended_editor = None
    else:
        provider = "missing"
        recommended_editor = ASECLI_GUI_EDITOR

    return {
        "project_root": str(project.root),
        "provider": provider,
        "providers": providers,
        "recommended_editor": recommended_editor,
        "native_mzgui": {
            "detected": bool(native_evidence),
            "editor": MZGUI_EDITOR,
            "evidence": native_evidence,
        },
        "asecli_compat": {
            "editor": ASECLI_GUI_EDITOR,
            "target": str(project.target),
            "asset_path": GUI_SUPPORT_ASSET_PATH,
            "state": target_state,
            "expected_sha256": GUI_SUPPORT_SHA256,
            "actual_sha256": actual_sha256,
        },
        "capabilities": {
            "foldout": "FoldoutMzgui",
            "tooltip": "TooltipMzgui",
            "help_box": "HelpBoxMzgui",
            "automatic_technical_tooltip": ["property_name", "shader_default_value"],
            "ase_version_dependency": False,
        },
        "would_write": not native_evidence and target_state == "absent",
        "written": False,
    }


def install_gui_support(project_root: str | Path, *, write: bool = False) -> dict:
    """Plan or install the fixed compatibility asset without overwriting files."""
    state = inspect_gui_support(project_root)
    target_state = state["asecli_compat"]["state"]
    if state["provider"] == "multiple":
        raise RuntimeError(
            "native MZGUI and ASECLI compatibility GUI are both installed; remove the fixed ASECLI asset "
            "before selecting MZGUI.MZGUI"
        )
    if state["native_mzgui"]["detected"]:
        state["action"] = "use_native_mzgui"
        state["would_write"] = False
        return state
    if target_state == "conflict":
        raise FileExistsError(
            "ASECLI GUI support target already exists with different content; refusing to overwrite: "
            + state["asecli_compat"]["target"]
        )
    if target_state == "installed":
        state["action"] = "already_installed"
        state["would_write"] = False
        return state

    state["action"] = "install_asecli_compat"
    if not write:
        return state

    project = _unity_project(project_root)
    project.target.parent.mkdir(parents=True, exist_ok=True)
    _assert_inside_project(project.target, project.root)
    try:
        descriptor = os.open(project.target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
    except FileExistsError as exc:
        raise FileExistsError(
            f"ASECLI GUI support target appeared during installation; refusing to overwrite: {project.target}"
        ) from exc
    opened_stat = os.fstat(descriptor)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="") as handle:
            handle.write(GUI_SUPPORT_SOURCE)
            handle.flush()
            os.fsync(handle.fileno())
    except Exception:
        try:
            current_stat = project.target.lstat()
            if (current_stat.st_dev, current_stat.st_ino) == (opened_stat.st_dev, opened_stat.st_ino):
                project.target.unlink()
        except FileNotFoundError:
            pass
        raise

    installed = inspect_gui_support(project_root)
    if installed["asecli_compat"]["state"] != "installed":
        raise RuntimeError("ASECLI GUI support was written but failed digest verification")
    installed["action"] = "install_asecli_compat"
    installed["would_write"] = False
    installed["written"] = True
    installed["requires_editor_recompile"] = True
    return installed


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


def _find_native_mzgui(project_root: Path) -> list[str]:
    search_roots = [project_root / "Assets", project_root / "Packages"]
    package_cache = project_root / "Library" / "PackageCache"
    if package_cache.is_dir():
        try:
            search_roots.extend(
                entry for entry in package_cache.iterdir() if "mzgui" in entry.name.lower()
            )
        except OSError:
            pass

    for root in search_roots:
        if not root.is_dir():
            continue
        for source in root.rglob("*.cs"):
            if source.name == Path(GUI_SUPPORT_ASSET_PATH).name:
                continue
            try:
                if source.stat().st_size > 2_000_000:
                    continue
                text = source.read_text(encoding="utf-8-sig", errors="ignore")
            except OSError:
                continue
            if _NATIVE_NAMESPACE_RE.search(text) and _NATIVE_GUI_RE.search(text):
                return [_relative_evidence(source, project_root)]
        for assembly in root.rglob("*.dll"):
            if "mzgui" in assembly.name.lower():
                return [_relative_evidence(assembly, project_root)]

    for manifest_name in ("manifest.json", "packages-lock.json"):
        manifest = project_root / "Packages" / manifest_name
        if not manifest.is_file():
            continue
        try:
            if "mzgui" in manifest.read_text(encoding="utf-8", errors="ignore").lower():
                return [_relative_evidence(manifest, project_root)]
        except OSError:
            continue
    return []


def _relative_evidence(path: Path, project_root: Path) -> str:
    try:
        return path.resolve().relative_to(project_root).as_posix()
    except ValueError:
        return str(path.resolve())
