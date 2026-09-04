"""Install the packaged ASECLI Agent Skill into a Codex skill directory."""

from __future__ import annotations

import hashlib
import os
import shutil
import uuid
from pathlib import Path

from .commands import CliError

SKILL_NAME = "asecli"


def _source_root() -> Path:
    """Return the skill shipped in the wheel, with a source-tree fallback."""
    packaged = Path(__file__).resolve().parents[1] / "skills" / SKILL_NAME
    if (packaged / "SKILL.md").is_file():
        return packaged
    source_tree = Path(__file__).resolve().parents[3] / "skills" / SKILL_NAME
    if (source_tree / "SKILL.md").is_file():
        return source_tree
    raise RuntimeError("packaged ASECLI Skill is missing")


def _skill_root(raw_root: str | None) -> Path:
    if raw_root:
        return Path(raw_root).expanduser()
    codex_home = os.environ.get("CODEX_HOME")
    return Path(codex_home).expanduser() / "skills" if codex_home else Path.home() / ".codex" / "skills"


def _regular_files(root: Path) -> list[Path]:
    if root.is_symlink() or not root.is_dir():
        raise ValueError(f"skill directory is not a regular directory: {root}")
    files = sorted(path for path in root.rglob("*") if path.is_file())
    if not files or not (root / "SKILL.md").is_file():
        raise ValueError(f"skill directory is incomplete: {root}")
    if any(path.is_symlink() for path in files):
        raise ValueError(f"skill directory contains a symbolic link: {root}")
    return files


def _tree_digest(root: Path) -> str:
    digest = hashlib.sha256()
    for path in _regular_files(root):
        relative = path.relative_to(root).as_posix().encode("utf-8")
        digest.update(len(relative).to_bytes(4, "big"))
        digest.update(relative)
        content = path.read_bytes()
        digest.update(len(content).to_bytes(8, "big"))
        digest.update(content)
    return digest.hexdigest()


def _ensure_regular_parent(root: Path) -> None:
    root.mkdir(parents=True, exist_ok=True)
    current = root
    while current != current.parent:
        if current.is_symlink():
            raise ValueError(f"skill root contains a symbolic link: {current}")
        current = current.parent


def install_skill(skill_root: str | None = None) -> dict:
    """Install the versioned skill once; refuse to replace unrelated content."""
    source = _source_root()
    source_digest = _tree_digest(source)
    root = _skill_root(skill_root)
    _ensure_regular_parent(root)
    target = root / SKILL_NAME
    if target.exists() or target.is_symlink():
        try:
            installed_digest = _tree_digest(target)
        except ValueError as exc:
            raise FileExistsError(f"existing Skill is unsafe or incomplete: {target}") from exc
        if installed_digest == source_digest:
            return {
                "installed": False,
                "status": "already_installed",
                "skill": SKILL_NAME,
                "path": str(target),
                "digest": source_digest,
            }
        raise FileExistsError(
            f"existing Skill differs from ASECLI {SKILL_NAME!r}: {target}; "
            "refusing to overwrite it"
        )

    staging = root / f".{SKILL_NAME}.staging-{uuid.uuid4().hex}"
    try:
        staging.mkdir()
        for source_path in _regular_files(source):
            relative = source_path.relative_to(source)
            destination = staging / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source_path, destination)
        if _tree_digest(staging) != source_digest:
            raise RuntimeError("copied Skill digest does not match packaged source")
        os.replace(staging, target)
    except Exception:
        if staging.exists() and not staging.is_symlink():
            shutil.rmtree(staging)
        raise
    return {
        "installed": True,
        "status": "installed",
        "skill": SKILL_NAME,
        "path": str(target),
        "digest": source_digest,
    }


def cmd_install_skill(args) -> dict:
    try:
        return install_skill(args.skill_root)
    except FileExistsError as exc:
        raise CliError("SKILL_INSTALL_CONFLICT", str(exc)) from exc
    except (OSError, RuntimeError, ValueError) as exc:
        raise CliError("SKILL_INSTALL_ERROR", str(exc)) from exc
