"""Descriptor-scoped file operations for the installed GUI resource."""

from __future__ import annotations

import os
from pathlib import Path
import stat

from ._gui_project import UnityProject


SECURE_DIRECTORY_OPERATIONS_AVAILABLE = (
    os.open in os.supports_dir_fd
    and os.mkdir in os.supports_dir_fd
    and hasattr(os, "O_NOFOLLOW")
)


def install_gui_resource(project: UnityProject, source: bytes) -> None:
    """Create the resource through verified directory descriptors only."""
    require_secure_directory_operations()
    descriptors: list[int] = []
    try:
        root_descriptor = open_directory(project.root)
        descriptors.append(root_descriptor)
        assets_descriptor = open_directory_at(root_descriptor, "Assets")
        descriptors.append(assets_descriptor)
        editor_descriptor = open_or_create_directory(assets_descriptor, "Editor")
        descriptors.append(editor_descriptor)
        support_descriptor = open_or_create_directory(editor_descriptor, "ASECLI")
        descriptors.append(support_descriptor)
        create_resource(support_descriptor, project.target, source)
        os.fsync(support_descriptor)
    finally:
        close_descriptors(descriptors)


def open_support_directory(project: UnityProject) -> list[int]:
    descriptors = [open_directory(project.root)]
    try:
        descriptors.append(open_directory_at(descriptors[-1], "Assets"))
        descriptors.append(open_directory_at(descriptors[-1], "Editor"))
        descriptors.append(open_directory_at(descriptors[-1], "ASECLI"))
        return descriptors
    except BaseException:
        close_descriptors(descriptors)
        raise


def close_descriptors(descriptors: list[int]) -> None:
    for descriptor in reversed(descriptors):
        os.close(descriptor)


def read_regular_resource(parent_descriptor: int, name: str) -> tuple[bytes, os.stat_result]:
    flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | os.O_NOFOLLOW
    descriptor = os.open(name, flags, dir_fd=parent_descriptor)
    opened_stat = os.fstat(descriptor)
    if not stat.S_ISREG(opened_stat.st_mode):
        os.close(descriptor)
        raise FileExistsError(f"ASECLI GUI support path is not a regular file: {name}")
    with os.fdopen(descriptor, "rb") as handle:
        return handle.read(), opened_stat


def create_exclusive_resource(
    parent_descriptor: int, name: str, content: bytes, mode: int
) -> os.stat_result:
    flags = (
        os.O_WRONLY
        | os.O_CREAT
        | os.O_EXCL
        | getattr(os, "O_CLOEXEC", 0)
        | os.O_NOFOLLOW
    )
    descriptor = os.open(name, flags, mode, dir_fd=parent_descriptor)
    opened_stat = os.fstat(descriptor)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
    except BaseException:
        unlink_created_resource(parent_descriptor, name, opened_stat)
        raise
    return opened_stat


def create_resource(parent_descriptor: int, target: Path, source: bytes) -> None:
    try:
        create_exclusive_resource(parent_descriptor, target.name, source, 0o644)
    except FileExistsError as exc:
        raise FileExistsError(
            f"ASECLI GUI support target appeared during installation; refusing to overwrite: {target}"
        ) from exc
    except FileNotFoundError as exc:
        raise RuntimeError(
            f"ASECLI GUI support directory changed during installation; refusing to write: {target}"
        ) from exc


def unlink_created_resource(
    parent_descriptor: int, name: str, opened_stat: os.stat_result
) -> None:
    try:
        current_stat = os.stat(name, dir_fd=parent_descriptor, follow_symlinks=False)
        if (current_stat.st_dev, current_stat.st_ino) == (
            opened_stat.st_dev,
            opened_stat.st_ino,
        ):
            os.unlink(name, dir_fd=parent_descriptor)
    except FileNotFoundError:
        pass


def require_secure_directory_operations() -> None:
    if not SECURE_DIRECTORY_OPERATIONS_AVAILABLE:
        raise RuntimeError(
            "secure ASECLI GUI installation requires dir_fd and O_NOFOLLOW support on this platform"
        )


def open_directory(path: Path) -> int:
    descriptor = os.open(path, _directory_flags())
    _require_directory(descriptor, path)
    return descriptor


def open_directory_at(parent_descriptor: int, name: str) -> int:
    descriptor = os.open(name, _directory_flags(), dir_fd=parent_descriptor)
    _require_directory(descriptor, Path(name))
    return descriptor


def open_or_create_directory(parent_descriptor: int, name: str) -> int:
    try:
        return open_directory_at(parent_descriptor, name)
    except FileNotFoundError:
        try:
            os.mkdir(name, mode=0o755, dir_fd=parent_descriptor)
        except FileExistsError:
            pass
        return open_directory_at(parent_descriptor, name)


def _directory_flags() -> int:
    return (
        os.O_RDONLY
        | getattr(os, "O_DIRECTORY", 0)
        | getattr(os, "O_CLOEXEC", 0)
        | os.O_NOFOLLOW
    )


def _require_directory(descriptor: int, path: Path) -> None:
    if stat.S_ISDIR(os.fstat(descriptor).st_mode):
        return
    os.close(descriptor)
    raise NotADirectoryError(f"ASECLI GUI support directory is not a directory: {path}")
