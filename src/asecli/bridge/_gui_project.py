"""Validated Unity project paths used by GUI support operations."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class UnityProject:
    root: Path
    assets: Path
    target: Path


def unity_project(project_root: str | Path, asset_path: str) -> UnityProject:
    root = Path(project_root).expanduser().resolve()
    if not root.is_dir():
        raise FileNotFoundError(f"Unity project root not found: {root}")
    assets = root / "Assets"
    settings = root / "ProjectSettings"
    if not assets.is_dir() or not settings.is_dir():
        raise ValueError("project root must contain Assets and ProjectSettings directories")
    _assert_inside_project(assets, root)
    target = root / asset_path
    _assert_inside_project(target, root)
    return UnityProject(root=root, assets=assets, target=target)


def _assert_inside_project(path: Path, project_root: Path) -> None:
    resolved = path.resolve(strict=False)
    try:
        resolved.relative_to(project_root)
    except ValueError as exc:
        raise ValueError(f"project path escapes through a symbolic link: {path}") from exc
