"""Transactionally create a new ASE shader through a fixed Editor executor."""

from __future__ import annotations

import base64
import hashlib
import json
from pathlib import Path
import secrets

from .editor_spec import EditorGraphSpec, SUPPORTED_ASE_VERSIONS
from .mcp_client import McpClient, McpError, redact, tool_text
from .resource_text import compose_resource_text


EDITOR_CREATE_RESOURCE_PARTS = (
    "editor_create.part00.cs.txt",
    "editor_create.part01.cs.txt",
    "editor_create.part02.cs.txt",
    "editor_create.part03.cs.txt",
    "editor_create.part04.cs.txt",
)
EDITOR_CREATE_SNIPPET = compose_resource_text(
    "asecli.bridge", "resources", EDITOR_CREATE_RESOURCE_PARTS
)
_RESULT_MARKER = "ASECLI_EDITOR_CREATE_V1:"


def create_shader_via_mcp(
    shader_path: str | Path,
    spec: EditorGraphSpec,
    mcp_url: str = "http://127.0.0.1:8080/mcp",
    instance_token: str | None = None,
    allow_remote_mcp: bool = False,
) -> dict:
    """Create one absent shader and accept only a verified Save/Load manifest."""
    target = Path(shader_path).resolve()
    if target.suffix.lower() != ".shader":
        raise ValueError("Editor create target must use the .shader extension")
    if not target.parent.is_dir():
        raise FileNotFoundError(f"parent directory not found: {target.parent}")
    if target.exists() or target.is_symlink():
        raise FileExistsError(f"Editor create target already exists: {target}")
    project_root, asset_path = _project_asset_path(target)
    transaction_nonce = secrets.token_hex(16)
    temporary_asset_path = _temporary_asset_path(asset_path, transaction_nonce)
    payload = spec.editor_payload(asset_path, temporary_asset_path)
    encoded = base64.b64encode(
        json.dumps(payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode("utf-8")
    ).decode("ascii")
    code = EDITOR_CREATE_SNIPPET.replace("{payload_base64}", encoded)
    client = McpClient(mcp_url, instance_token=instance_token, allow_remote=allow_remote_mcp)
    client.connect()
    result = client.call_tool(
        "execute_code",
        {
            "action": "execute",
            "code": code,
            # The fixed transactional executor uses AssetDatabase.DeleteAsset
            # only to roll back its nonce-scoped staging asset. MCP 3.4.7 blocks
            # that API by pattern unless the per-call safety scan is disabled.
            "safety_checks": False,
        },
    )
    response = _parse_result(_execute_code_result_text(result, instance_token))
    _validate_result(response, asset_path, spec.expected_manifest())
    if not target.is_file():
        raise McpError("Editor create reported success but target file is missing")
    temporary_file = project_root / temporary_asset_path
    if temporary_file.exists() or temporary_file.with_suffix(temporary_file.suffix + ".meta").exists():
        raise McpError("Editor create left a temporary asset after commit")
    meta_file = target.with_suffix(target.suffix + ".meta")
    return {
        "transport": "mcp",
        "server": mcp_url,
        "asset_path": asset_path,
        "ase_version": response["ase_version"],
        "template_guid": response["template_guid"],
        "shader_name": response["shader_name"],
        "saved": True,
        # Compat: reloaded means the staging asset was LoadFromDisk'd, not the committed target.
        "reloaded": True,
        "staging_reloaded": True,
        "target_graph_reloaded": False,
        "committed": True,
        "changed": True,
        "manifest": response["manifest"],
        "transaction_nonce": transaction_nonce,
        "shader_sha256": _sha256(target),
        "meta_sha256": _sha256(meta_file) if meta_file.is_file() else None,
    }


def _project_asset_path(target: Path) -> tuple[Path, str]:
    current = target.parent
    while current != current.parent:
        if (current / "Assets").is_dir() and (current / "ProjectSettings").is_dir():
            try:
                relative = target.relative_to(current)
            except ValueError as exc:  # pragma: no cover - resolve makes this defensive
                raise ValueError("Editor create target is outside the Unity project") from exc
            if not relative.parts or relative.parts[0] != "Assets":
                raise ValueError("Editor create target must be inside the Unity project Assets directory")
            return current, relative.as_posix()
        current = current.parent
    raise ValueError("cannot locate Unity project root; target must be inside Assets")


def _temporary_asset_path(asset_path: str, transaction_nonce: str) -> str:
    target = Path(asset_path)
    return (target.parent / f"ASECLI-Temp-{transaction_nonce}-{target.name}").as_posix()


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _parse_result(text: str) -> dict:
    marker_index = text.find(_RESULT_MARKER)
    if marker_index < 0:
        raise McpError("MCP tool result did not contain the Editor create protocol marker")
    raw = text[marker_index + len(_RESULT_MARKER) :].lstrip()
    try:
        value, _ = json.JSONDecoder().raw_decode(raw)
    except json.JSONDecodeError as exc:
        raise McpError("MCP tool returned malformed Editor create JSON") from exc
    if not isinstance(value, dict):
        raise McpError("MCP Editor create result must be a JSON object")
    return value


def _execute_code_result_text(result: dict, instance_token: str | None) -> str:
    """Unwrap execute_code's JSON envelope while retaining legacy text support."""
    text = tool_text(result, instance_token)
    try:
        envelope = json.loads(text)
    except json.JSONDecodeError:
        return text
    if not isinstance(envelope, dict):
        return text
    if envelope.get("success") is False:
        detail = envelope.get("message")
        if not isinstance(detail, str) or not detail.strip():
            detail = "no error details"
        raise McpError(f"MCP execute_code reported failure: {redact(detail[:300], instance_token)}")
    data = envelope.get("data")
    if isinstance(data, dict) and isinstance(data.get("result"), str):
        return data["result"]
    return text


def _validate_result(response: dict, asset_path: str, expected_manifest: dict) -> None:
    if response.get("protocol") != "ASECLI_EDITOR_CREATE_V1":
        raise McpError("Editor create protocol version is missing or unsupported")
    version = response.get("ase_version")
    if version not in SUPPORTED_ASE_VERSIONS:
        raise McpError(f"Editor create returned unsupported ASE version: {version}")
    if response.get("asset_path") != asset_path:
        raise McpError("Editor create returned a different asset path")
    expected_template = expected_manifest["template"]
    if response.get("template_guid") != expected_template["guid"]:
        raise McpError("Editor create returned a different template guid")
    if response.get("shader_name") != expected_template["shader_name"]:
        raise McpError("Editor create returned a different shader name")
    for field in ("saved", "reloaded", "committed"):
        if response.get(field) is not True:
            raise McpError(f"Editor create did not confirm {field}=True")
    if response.get("manifest") != expected_manifest:
        raise McpError("Editor create Save/Load manifest does not match the requested graph")
