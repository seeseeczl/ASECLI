"""Choose which editor transport to drive.

Every transport is an external process or mailbox; this module only decides
which one to use, never changing their behaviour.
"""

from __future__ import annotations

import time
from pathlib import Path

from .codely_client import CodelyClient, CodelyError
from .bridge_client import BridgeClient, BridgeError
from .bridge_probe import probe as bridge_probe
from .codely_probe import probe as codely_probe
from .codely_discovery import DiscoveryError, find_project_root
from .editor_result import RESULT_KEYS, EditorExecutionError, extract_payload
from .mcp_client import McpClient, McpError, tool_text

BACKENDS = ("auto", "mcp", "codely", "bridge")
CODELY_HINT = "install cn.tuanjie.codely.bridge and open the project, or pass --mcp-url"


#: How long a successful ``auto`` decision is reused, so repeated commands in
#: one session do not re-probe every transport (AA-OPT-012).
CHOICE_TTL = 30.0
#: A failed sweep is reused briefly: probing all three backends costs up to
#: their combined timeouts, and back-to-back commands should not each pay it.
FAILURE_TTL = 5.0
_choice_cache: dict[tuple, tuple[float, str, dict]] = {}


def clear_backend_cache() -> None:
    """Forget cached decisions (tests and long-lived processes)."""
    _choice_cache.clear()


class BackendError(RuntimeError):
    """Raised when no usable editor backend can be resolved."""

    def __init__(self, message: str, *, attempts: list[dict] | None = None):
        super().__init__(message)
        self.attempts = attempts or []


def _remember(key, backend: str, details: dict) -> tuple[str, dict]:
    _choice_cache[key] = (time.monotonic() + CHOICE_TTL, backend, details)
    return backend, details


def resolve_project_root(target: str | Path) -> Path:
    """Locate the Unity project root for *target*."""
    resolved = Path(target).resolve()
    root = find_project_root(resolved)
    if root is None:
        raise BackendError(
            f"cannot locate a Unity project (needs Assets and ProjectSettings) from {resolved}"
        )
    return root


def probe_mcp(url: str, instance_token: str | None = None, allow_remote: bool = False) -> dict:
    """Connect to mcp-for-unity and report whether it answers."""
    try:
        McpClient(url, instance_token=instance_token, allow_remote=allow_remote).connect()
        return {"ok": True, "reason": None}
    except Exception as exc:  # defensive: probing must never raise
        return {"ok": False, "reason": f"{type(exc).__name__}: {exc}"}


def select_backend(
    requested: str,
    target: str | Path,
    *,
    mcp_url: str = "http://127.0.0.1:8080/mcp",
    instance_token: str | None = None,
    allow_remote_mcp: bool = False,
    codely_port: int | None = None,
) -> tuple[str, dict]:
    """Resolve which editor transport to use, returning ``(name, details)``.

    An explicit backend never falls back silently, so a caller cannot believe it
    drove one editor while actually reaching another.
    """
    if requested not in BACKENDS:
        raise BackendError(f"unknown backend {requested!r}; expected one of {', '.join(BACKENDS)}")

    if requested == "mcp":
        return "mcp", {"server": mcp_url}
    if requested == "codely":
        return "codely", {"project_root": str(resolve_project_root(target))}
    if requested == "bridge":
        return "bridge", {"project_root": str(resolve_project_root(target))}
    # auto: try each resident bridge in turn, then fall back to a standalone server.
    # Key on the resolved project root (raw targets with ".." resolve
    # lexically) and on the credentials deciding which MCP instance we reach.
    try:
        cache_root = str(resolve_project_root(target))
    except BackendError:
        cache_root = ""
    cache_key = (cache_root, mcp_url, codely_port, instance_token, allow_remote_mcp)
    cached = _choice_cache.get(cache_key)
    if cached and cached[0] > time.monotonic():
        if cached[1]:
            return cached[1], dict(cached[2])
        reasons = "; ".join(
            f"{i['backend']}: {i.get('reason', 'unavailable')}" for i in cached[2]["attempts"]
        )
        raise BackendError(f"no editor backend available ({reasons})", attempts=cached[2]["attempts"])
    attempts: list[dict] = []
    try:
        root = resolve_project_root(target)
    except BackendError as exc:
        root = None
        attempts.append({"backend": "bridge", "ok": False, "reason": str(exc)})
    if root is not None:
        bridge_result = bridge_probe(root)
        attempts.append({"backend": "bridge", **bridge_result})
        if bridge_result["ok"]:
            return _remember(cache_key, "bridge", {"project_root": str(root), "probe": bridge_result})

        codely_result = codely_probe(root, port=codely_port)
        attempts.append({"backend": "codely", **codely_result})
        if codely_result["ok"]:
            return _remember(cache_key, "codely", {"project_root": str(root), "probe": codely_result})

    mcp_result = probe_mcp(mcp_url, instance_token, allow_remote_mcp)
    attempts.append({"backend": "mcp", **mcp_result})
    if mcp_result["ok"]:
        return _remember(cache_key, "mcp", {"server": mcp_url, "probe": mcp_result})

    summary = "; ".join(
        f"{item['backend']}: {'ok' if item['ok'] else item.get('reason', 'unavailable')}"
        for item in attempts
    )
    # Remember the failure briefly so consecutive commands fail fast instead of
    # each paying every transport's timeout.
    _choice_cache[cache_key] = (time.monotonic() + FAILURE_TTL, "", {"attempts": attempts})
    raise BackendError(f"no editor backend available ({summary})", attempts=attempts)


def open_transport(
    backend: str,
    target: str | Path,
    *,
    details: dict | None = None,
    mcp_url: str = "http://127.0.0.1:8080/mcp",
    instance_token: str | None = None,
    allow_remote_mcp: bool = False,
    codely_port: int | None = None,
    mcp_factory=None,
):
    """Return a connected client for *backend*."""
    details = details or {}
    if backend == "bridge":
        client = BridgeClient(details.get("project_root") or target)
        client.connect()
        return client
    if backend == "codely":
        client = CodelyClient(details.get("project_root") or target, port=codely_port)
        client.connect()
        return client
    factory = mcp_factory or McpClient
    client = factory(mcp_url, instance_token=instance_token, allow_remote=allow_remote_mcp)
    client.connect()
    return client


def run_code(
    client,
    code: str,
    backend: str,
    instance_token: str | None = None,
    unity_instance: str | None = None,
) -> str:
    """Execute *code* on either transport and return its textual response.

    ``unity_instance`` is an mcp-for-unity concept; Codely addresses the single
    editor that owns the project's port registry, so it is rejected rather than
    silently ignored.
    """
    if backend in ("bridge", "codely"):
        if unity_instance is not None:
            raise BackendError(
                f"unity_instance is not supported by the {backend} backend; it "
                "addresses the editor that owns the project's instance record"
            )
        return client.execute_code(code)
    arguments = {"action": "execute", "code": code}
    if unity_instance is not None:
        arguments["unity_instance"] = unity_instance
    return tool_text(client.call_tool("execute_code", arguments), instance_token)


def run_editor_code(
    target: str | Path,
    code: str,
    *,
    backend: str = "auto",
    mcp_url: str = "http://127.0.0.1:8080/mcp",
    instance_token: str | None = None,
    allow_remote_mcp: bool = False,
    codely_port: int | None = None,
    unity_instance: str | None = None,
    mcp_factory=None,
    mcp_executor=None,
) -> tuple[str, str]:
    """Resolve a backend, execute *code* once, and return ``(text, backend)``.

    ``mcp_factory`` and ``mcp_executor`` let callers inject their own client and
    tool invocation, which the Editor-create path needs for its safety-scan
    retry and tests need for patching.
    """
    effective = backend
    if backend == "auto" and unity_instance is not None:
        # Codely has no multi-instance addressing, so an explicit instance
        # selector only makes sense on mcp-for-unity.
        effective = "mcp"
    resolved, details = select_backend(
        effective,
        target,
        mcp_url=mcp_url,
        instance_token=instance_token,
        allow_remote_mcp=allow_remote_mcp,
        codely_port=codely_port,
    )
    client = open_transport(
        resolved,
        target,
        details=details,
        mcp_url=mcp_url,
        instance_token=instance_token,
        allow_remote_mcp=allow_remote_mcp,
        codely_port=codely_port,
        mcp_factory=mcp_factory,
    )
    try:
        if resolved == "mcp" and mcp_executor is not None:
            text = tool_text(mcp_executor(client, code), instance_token)
        else:
            text = run_code(client, code, resolved, instance_token, unity_instance)
    finally:
        close = getattr(client, "close", None)
        if callable(close):
            close()
    if resolved in ("bridge", "codely"):
        # Both transports return the script's own string, not an MCP envelope.
        text = extract_payload(text, "raw")
    return text, resolved
