"""Recoverable atomic upgrade for known ASECLI GUI resource revisions."""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
import stat

from ._gui_project import UnityProject
from ._gui_resource_store import (
    close_descriptors,
    create_exclusive_resource,
    open_support_directory,
    read_regular_resource,
    require_secure_directory_operations,
    unlink_created_resource,
)


def upgrade_backup_path(
    target: Path, digest: str | None, known_previous: dict[str, str]
) -> Path | None:
    if digest not in known_previous:
        return None
    return target.with_name(f"{target.name}.asecli-backup-{digest[:12]}")


def upgrade_gui_resource(
    project: UnityProject,
    source: bytes,
    expected_digest: str | None,
    known_previous: dict[str, str],
) -> Path:
    """Back up one known resource, revalidate it, then atomically replace it."""
    if expected_digest not in known_previous:
        raise FileExistsError(
            f"ASECLI GUI support target is not a known upgrade source: {project.target}"
        )
    require_secure_directory_operations()
    descriptors = open_support_directory(project)
    parent_descriptor = descriptors[-1]
    temporary_name = project.target.name + ".asecli-upgrade.tmp"
    temporary_stat: os.stat_result | None = None
    try:
        original, original_stat = read_regular_resource(
            parent_descriptor, project.target.name
        )
        _require_digest(project.target, original, expected_digest)
        backup_path = upgrade_backup_path(
            project.target, expected_digest, known_previous
        )
        assert backup_path is not None
        _create_or_verify_backup(
            parent_descriptor,
            backup_path.name,
            original,
            original_stat,
            expected_digest,
        )
        os.fsync(parent_descriptor)
        try:
            temporary_stat = create_exclusive_resource(
                parent_descriptor,
                temporary_name,
                source,
                stat.S_IMODE(original_stat.st_mode),
            )
        except FileExistsError as exc:
            raise FileExistsError(
                f"ASECLI GUI support upgrade temporary already exists; refusing to overwrite: {temporary_name}"
            ) from exc
        current, current_stat = read_regular_resource(
            parent_descriptor, project.target.name
        )
        _require_digest(project.target, current, expected_digest)
        if (current_stat.st_dev, current_stat.st_ino) != (
            original_stat.st_dev,
            original_stat.st_ino,
        ):
            raise FileExistsError(
                f"ASECLI GUI support target changed during upgrade; refusing to overwrite: {project.target}"
            )
        os.replace(
            temporary_name,
            project.target.name,
            src_dir_fd=parent_descriptor,
            dst_dir_fd=parent_descriptor,
        )
        temporary_stat = None
        os.fsync(parent_descriptor)
        return backup_path
    finally:
        if temporary_stat is not None:
            unlink_created_resource(parent_descriptor, temporary_name, temporary_stat)
        close_descriptors(descriptors)


def _require_digest(target: Path, content: bytes, expected_digest: str) -> None:
    if hashlib.sha256(content).hexdigest() != expected_digest:
        raise FileExistsError(
            f"ASECLI GUI support target changed during upgrade; refusing to overwrite: {target}"
        )


def _create_or_verify_backup(
    parent_descriptor: int,
    name: str,
    content: bytes,
    source_stat: os.stat_result,
    expected_digest: str,
) -> None:
    try:
        create_exclusive_resource(
            parent_descriptor, name, content, stat.S_IMODE(source_stat.st_mode)
        )
    except FileExistsError:
        existing, _ = read_regular_resource(parent_descriptor, name)
        if hashlib.sha256(existing).hexdigest() != expected_digest:
            raise FileExistsError(
                f"ASECLI GUI support backup already exists with different content: {name}"
            )
