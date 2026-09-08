"""Install the packaged ASECLI Agent Skill for supported coding agents."""

from __future__ import annotations

import hashlib
import os
import shutil
import uuid
from pathlib import Path

from .commands import CliError

SKILL_NAME = "asecli"
AGENT_CHOICES = ("agents", "codex", "claude", "cursor", "gemini", "copilot", "all")
SCOPE_CHOICES = ("user", "project")

_AGENT_RELATIVE_ROOTS = {
    "agents": (".agents", "skills"),
    "codex": (".agents", "skills"),
    "claude": (".claude", "skills"),
    "cursor": (".cursor", "skills"),
    "gemini": (".gemini", "skills"),
    "copilot": (".copilot", "skills"),
}

_PROJECT_RELATIVE_ROOTS = {
    **_AGENT_RELATIVE_ROOTS,
    "copilot": (".github", "skills"),
}

_COMPATIBLE_AGENTS = {
    "agents": ["codex", "cursor", "gemini-cli", "github-copilot"],
    "codex": ["codex"],
    "claude": ["claude-code"],
    "cursor": ["cursor"],
    "gemini": ["gemini-cli"],
    "copilot": ["github-copilot"],
}


def _source_root() -> Path:
    """Return the skill shipped in the wheel, with a source-tree fallback."""
    packaged = Path(__file__).resolve().parents[1] / "skills" / SKILL_NAME
    if (packaged / "SKILL.md").is_file():
        return packaged
    source_tree = Path(__file__).resolve().parents[3] / "skills" / SKILL_NAME
    if (source_tree / "SKILL.md").is_file():
        return source_tree
    raise RuntimeError("packaged ASECLI Skill is missing")


def _legacy_skill_root(raw_root: str | None) -> Path:
    if raw_root:
        return Path(raw_root).expanduser()
    codex_home = os.environ.get("CODEX_HOME")
    return Path(codex_home).expanduser() / "skills" if codex_home else Path.home() / ".codex" / "skills"


def _project_base(raw_project_root: str | None) -> Path:
    base = Path(raw_project_root).expanduser() if raw_project_root else Path.cwd()
    return base if base.is_absolute() else Path.cwd() / base


def _agent_skill_root(agent: str, scope: str, project_root: str | None) -> Path:
    if scope == "project":
        return _project_base(project_root).joinpath(*_PROJECT_RELATIVE_ROOTS[agent])
    return Path.home().joinpath(*_AGENT_RELATIVE_ROOTS[agent])


def _destinations(agent: str, scope: str, project_root: str | None) -> list[tuple[str, Path]]:
    if agent not in AGENT_CHOICES:
        raise ValueError(f"unsupported agent: {agent}")
    if scope not in SCOPE_CHOICES:
        raise ValueError(f"unsupported skill scope: {scope}")
    if project_root and scope != "project":
        raise ValueError("--project-root requires --scope project")

    # The open .agents location is shared by Codex, Cursor, Gemini CLI, and
    # GitHub Copilot. Claude Code needs one additional native destination.
    selected = ("agents", "claude") if agent == "all" else (agent,)
    return [(name, _agent_skill_root(name, scope, project_root)) for name in selected]


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


def _inspect_target(target: Path, source_digest: str) -> str:
    if not target.exists() and not target.is_symlink():
        return "missing"
    try:
        installed_digest = _tree_digest(target)
    except ValueError as exc:
        raise FileExistsError(f"existing Skill is unsafe or incomplete: {target}") from exc
    if installed_digest == source_digest:
        return "already_installed"
    raise FileExistsError(
        f"existing Skill differs from ASECLI {SKILL_NAME!r}: {target}; "
        "refusing to overwrite it"
    )


def _install_destination(source: Path, source_digest: str, root: Path, agent: str, scope: str) -> dict:
    _ensure_regular_parent(root)
    target = root / SKILL_NAME
    if _inspect_target(target, source_digest) == "already_installed":
        return {
            "installed": False,
            "status": "already_installed",
            "skill": SKILL_NAME,
            "agent": agent,
            "compatible_agents": _COMPATIBLE_AGENTS[agent],
            "scope": scope,
            "path": str(target),
            "digest": source_digest,
        }

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
        "agent": agent,
        "compatible_agents": _COMPATIBLE_AGENTS[agent],
        "scope": scope,
        "path": str(target),
        "digest": source_digest,
    }


def install_skill(
    skill_root: str | None = None,
    *,
    agent: str | None = None,
    scope: str = "user",
    project_root: str | None = None,
) -> dict:
    """Install the versioned Skill once; refuse to replace unrelated content.

    With no new routing options this preserves the original Codex destination.
    Explicit agent routing supports native and open Agent Skills directories.
    """
    if skill_root and (agent or scope != "user" or project_root):
        raise ValueError("--skill-root cannot be combined with --agent, --scope, or --project-root")

    source = _source_root()
    source_digest = _tree_digest(source)
    if skill_root or agent is None:
        destinations = [("codex", _legacy_skill_root(skill_root))]
    else:
        destinations = _destinations(agent, scope, project_root)

    # Refuse all content conflicts before creating any destination for --agent all.
    for _, root in destinations:
        _inspect_target(root / SKILL_NAME, source_digest)

    results = [
        _install_destination(source, source_digest, root, destination_agent, scope)
        for destination_agent, root in destinations
    ]
    if len(results) == 1:
        return results[0]
    installed_count = sum(1 for result in results if result["installed"])
    return {
        "installed": installed_count > 0,
        "status": "installed" if installed_count else "already_installed",
        "skill": SKILL_NAME,
        "agent": "all",
        "compatible_agents": ["codex", "claude-code", "cursor", "gemini-cli", "github-copilot"],
        "scope": scope,
        "installed_count": installed_count,
        "targets": results,
        "digest": source_digest,
    }


def cmd_install_skill(args) -> dict:
    try:
        scope = args.scope or "user"
        agent = args.agent
        if agent is None and (args.scope or args.project_root):
            agent = "agents"
        return install_skill(
            args.skill_root,
            agent=agent,
            scope=scope,
            project_root=args.project_root,
        )
    except FileExistsError as exc:
        raise CliError("SKILL_INSTALL_CONFLICT", str(exc)) from exc
    except (OSError, RuntimeError, ValueError) as exc:
        raise CliError("SKILL_INSTALL_ERROR", str(exc)) from exc
