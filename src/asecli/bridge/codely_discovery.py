"""Locate a Unity/Tuanjie project and the Codely Bridge port that serves it.

Codely Bridge persists its TCP port in a registry file at the project root
(``.com-unity-codely.json``), with a legacy per-project fallback.

**Ownership is enforced.**  Codely also writes a user-level registry under
``~/.unity-tcp/`` that reflects whichever project ran last.  Reading that file
would silently target a different project's editor, so it is deliberately never
consulted; a registry is only accepted when it belongs to the requested project.
"""

from __future__ import annotations

import json
from pathlib import Path

PORT_REGISTRY_NAME = ".com-unity-codely.json"
LEGACY_REGISTRY_NAMES = ("unity-tcp-port.json",)


class DiscoveryError(RuntimeError):
    """Raised when a project root or Codely port cannot be resolved."""

    def __init__(self, message: str, *, data: dict | None = None):
        super().__init__(message)
        self.data = data or {}


def find_project_root(start: Path) -> Path | None:
    """Walk up from *start* to the first directory holding Assets and ProjectSettings."""
    current = start if start.is_dir() else start.parent
    for candidate in (current, *current.parents):
        if (candidate / "Assets").is_dir() and (candidate / "ProjectSettings").is_dir():
            return candidate
    return None


def registry_candidates(project_root: Path) -> list[Path]:
    """Registry paths belonging to *project_root*, most specific first.

    Only project-scoped paths are returned: a registry outside the project
    cannot be attributed to it, so accepting one would risk driving another
    project's editor.
    """
    candidates = [project_root / PORT_REGISTRY_NAME]
    candidates.extend(project_root / name for name in LEGACY_REGISTRY_NAMES)
    return candidates


def _registry_belongs(project_root: Path, data: dict) -> bool:
    """True when *data* describes *project_root* (or declares no path at all)."""
    declared = data.get("project_path")
    if not isinstance(declared, str) or not declared.strip():
        # Older registries omit the field; the file location already scopes it.
        return True
    declared_path = Path(declared).expanduser().resolve()
    project_assets = (project_root / "Assets").resolve()
    # Codely records either the Assets directory or the project root itself.
    return declared_path in (project_assets, project_root.resolve())


def read_port_registry(project_root: Path) -> dict | None:
    """Return the Codely port registry for *project_root*, or None.

    Registries that declare a different project are ignored, so a copied or
    stale file can never redirect ASECLI to another editor.
    """
    project_root = project_root.resolve()
    for candidate in registry_candidates(project_root):
        try:
            if not candidate.is_file():
                continue
            data = json.loads(candidate.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(data, dict) or not isinstance(data.get("unity_port"), int):
            continue
        if not _registry_belongs(project_root, data):
            continue
        return data
    return None


def describe_foreign_registry(project_root: Path) -> str | None:
    """Explain a rejected registry so the caller can report why discovery failed."""
    for candidate in registry_candidates(project_root):
        try:
            if not candidate.is_file():
                continue
            data = json.loads(candidate.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if isinstance(data, dict) and not _registry_belongs(project_root.resolve(), data):
            return (
                f"{candidate} belongs to {data.get('project_path')!r}, "
                f"not to {project_root}; refusing to target another project's editor"
            )
    return None


def discover_port(project_root: Path) -> int:
    """Resolve the Codely TCP port for *project_root*."""
    registry = read_port_registry(project_root)
    if registry is None:
        foreign = describe_foreign_registry(project_root)
        if foreign:
            raise DiscoveryError(foreign)
        raise DiscoveryError(
            f"no Codely Bridge port registry under {project_root}; "
            "install cn.tuanjie.codely.bridge or open the project in the editor"
        )
    port = int(registry["unity_port"])
    if not 0 < port < 65536:
        raise DiscoveryError(f"Codely port {port} out of range")
    if registry.get("reloading") is True:
        raise DiscoveryError(
            f"Codely Bridge for {project_root} is reloading assemblies; retry once the editor settles"
        )
    return port
