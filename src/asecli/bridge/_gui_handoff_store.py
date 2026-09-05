"""Descriptor-scoped reversible disable/restore for a known GUI fallback."""

from __future__ import annotations

import hashlib
import os
from pathlib import Path

from ._gui_project import UnityProject
from ._gui_resource_store import (
    close_descriptors,
    open_support_directory,
    read_regular_resource,
    require_secure_directory_operations,
)


def handoff_backup_path(target: Path, digest: str) -> Path:
    return target.with_name(f"{target.name}.asecli-handoff-{digest[:12]}.disabled")


def disable_known_fallback(
    project: UnityProject, expected_digest: str, known_digests: set[str]
) -> Path:
    if expected_digest not in known_digests:
        raise FileExistsError("fallback digest is not eligible for native handoff")
    return _rename_verified(project, project.target, handoff_backup_path(project.target, expected_digest), expected_digest)


def restore_known_fallback(
    project: UnityProject, backup: Path, expected_digest: str, known_digests: set[str]
) -> Path:
    if expected_digest not in known_digests:
        raise FileExistsError("fallback digest is not eligible for handoff restore")
    return _rename_verified(project, backup, project.target, expected_digest)


def remove_known_resource(project: UnityProject, target: Path, expected_digest: str) -> None:
    require_secure_directory_operations()
    descriptors = open_support_directory(project)
    parent = descriptors[-1]
    try:
        content, opened = read_regular_resource(parent, target.name)
        if hashlib.sha256(content).hexdigest() != expected_digest:
            raise FileExistsError(f"GUI handoff resource changed; refusing to remove: {target}")
        current = os.stat(target.name, dir_fd=parent, follow_symlinks=False)
        if (current.st_dev, current.st_ino) != (opened.st_dev, opened.st_ino):
            raise FileExistsError(f"GUI handoff resource changed; refusing to remove: {target}")
        os.unlink(target.name, dir_fd=parent)
        os.fsync(parent)
    finally:
        close_descriptors(descriptors)


def _rename_verified(
    project: UnityProject, source: Path, destination: Path, expected_digest: str
) -> Path:
    require_secure_directory_operations()
    descriptors = open_support_directory(project)
    parent = descriptors[-1]
    try:
        content, opened = read_regular_resource(parent, source.name)
        if hashlib.sha256(content).hexdigest() != expected_digest:
            raise FileExistsError(f"GUI handoff source changed; refusing to move: {source}")
        try:
            os.stat(destination.name, dir_fd=parent, follow_symlinks=False)
        except FileNotFoundError:
            pass
        else:
            raise FileExistsError(f"GUI handoff destination already exists: {destination}")
        current = os.stat(source.name, dir_fd=parent, follow_symlinks=False)
        if (current.st_dev, current.st_ino) != (opened.st_dev, opened.st_ino):
            raise FileExistsError(f"GUI handoff source changed; refusing to move: {source}")
        os.rename(source.name, destination.name, src_dir_fd=parent, dst_dir_fd=parent)
        os.fsync(parent)
        return destination
    finally:
        close_descriptors(descriptors)
