"""Transactionally create a new ASE shader through a fixed Editor executor."""

from __future__ import annotations

import base64
import hashlib
import gzip
import math
import json
from pathlib import Path
import secrets

from .editor_spec import EditorGraphSpec, SUPPORTED_ASE_VERSIONS
from .backend import EditorExecutionError, extract_payload, run_editor_code
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
    *,
    backend: str = "auto",
    codely_port: int | None = None,
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
    # Only mcp-for-unity rejects oversized payloads; the other transports are
    # far more permissive, so do not impose its ceiling on them.
    code = build_executor_code(payload, limit=MCP_CODE_LIMIT if backend == "mcp" else None)
    result_text, used = run_editor_code(
        target,
        code,
        backend=backend,
        mcp_url=mcp_url,
        instance_token=instance_token,
        allow_remote_mcp=allow_remote_mcp,
        codely_port=codely_port,
        mcp_factory=McpClient,
        mcp_executor=call_execute_code,
    )
    try:
        payload_text = extract_payload(result_text, used)
    except EditorExecutionError as exc:
        raise McpError(str(exc)) from exc
    response = _parse_result(payload_text)
    _validate_result(response, asset_path, spec.expected_manifest())
    if not target.is_file():
        raise McpError("Editor create reported success but target file is missing")
    temporary_file = project_root / temporary_asset_path
    if temporary_file.exists() or temporary_file.with_suffix(temporary_file.suffix + ".meta").exists():
        raise McpError("Editor create left a temporary asset after commit")
    meta_file = target.with_suffix(target.suffix + ".meta")
    return {
        "transport": used,
        "server": mcp_url if used == "mcp" else "codely",
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


#: mcp-for-unity rejects oversized execute_code payloads; other transports
#: (mailbox, TCP) have far higher ceilings, so the limit is per-backend.
MCP_CODE_LIMIT = 50000


def build_executor_code(payload: dict, *, limit: int | None = MCP_CODE_LIMIT) -> str:
    """压缩大图的 JSON，固定执行器仍完整留在受控代码内。"""
    raw = json.dumps(payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode("utf-8")
    # 固定资源仅含单行字符串；去掉行首缩进不改动任何字符串内容。
    snippet = "\n".join(line.strip() for line in EDITOR_CREATE_SNIPPET.splitlines()
                        if line.strip() and not line.lstrip().startswith("//"))
    encoded = base64.b64encode(raw).decode("ascii")
    code = snippet.replace("{payload_base64}", encoded)
    threshold = limit if limit is not None else 0
    if limit is not None and len(code) > threshold:
        encoded = base64.b64encode(gzip.compress(raw, mtime=0)).decode("ascii")
        first_line = snippet.split("\n", 1)[0]
        unpack = ('string payloadJson;\n'
                  'using (var compressed = new System.IO.MemoryStream(System.Convert.FromBase64String("{payload_base64}")))\n'
                  'using (var gzip = new System.IO.Compression.GZipStream(compressed, System.IO.Compression.CompressionMode.Decompress))\n'
                  'using (var reader = new System.IO.StreamReader(gzip, System.Text.Encoding.UTF8)) payloadJson = reader.ReadToEnd();')
        code = snippet.replace(first_line, unpack, 1).replace("{payload_base64}", encoded)
    if limit is not None and len(code) > limit:
        raise ValueError(
            f"compressed Editor create request is {len(code)} characters, over the "
            f"{limit}-character limit this transport enforces"
        )
    return code


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
        raise McpError("editor result did not contain the Editor create protocol marker")
    raw = text[marker_index + len(_RESULT_MARKER) :].lstrip()
    try:
        value, _ = json.JSONDecoder().raw_decode(raw)
    except json.JSONDecodeError as exc:
        raise McpError("editor returned malformed Editor create JSON") from exc
    if not isinstance(value, dict):
        raise McpError("Editor create result must be a JSON object")
    return value


def call_execute_code(client, code: str) -> dict:
    """Call ``execute_code`` by capability, never by server version.

    The transactional executor needs ``AssetDatabase.DeleteAsset`` for its
    nonce-scoped staging rollback, which pattern-scanning servers reject unless
    the safety scan is disabled.  A rejected argument fails validation before
    any C# runs, so one retry without it is safe.
    """
    arguments = {"action": "execute", "code": code, "safety_checks": False}
    try:
        return client.call_tool("execute_code", arguments)
    except McpError as exc:
        if not _rejects_unknown_argument(exc):
            raise
        arguments.pop("safety_checks")
        try:
            return client.call_tool("execute_code", arguments)
        except McpError:
            # Surface the original rejection: the retry without the opt-out is
            # less likely to be the informative failure.
            raise exc from None


def _rejects_unknown_argument(exc: McpError) -> bool:
    """True only for a schema/argument rejection, never for a tool failure."""
    text = f"{exc} {getattr(exc, 'data', '')}".lower()
    return "safety_checks" in text and any(
        marker in text
        for marker in (
            "unknown", "unexpected", "unsupported", "not allowed", "not permitted",
            "additional propert", "invalid argument", "invalid parameter",
            "invalid_request", "unrecognized", "no such",
        )
    )


def _execute_code_result_text(result: dict, instance_token: str | None) -> str:
    """Unwrap execute_code's JSON envelope while retaining legacy text support."""
    text = tool_text(result, instance_token)
    try:
        return extract_payload(text, "mcp")
    except EditorExecutionError as exc:
        raise McpError(f"editor execute_code reported failure: {redact(str(exc)[:300], instance_token)}") from exc


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
    if not manifests_match(response.get("manifest"), expected_manifest):
        raise McpError("Editor create Save/Load manifest does not match the requested graph",
                       data={"actual_manifest": response.get("manifest"), "expected_manifest": expected_manifest})


def manifests_match(actual, expected, numeric=False):
    """仅容忍 ASE 单精度数值序列化的舍入；类型、端口与代码仍精确比较。"""
    if isinstance(expected, dict):
        return isinstance(actual, dict) and actual.keys() == expected.keys() and all(
            manifests_match(actual[k], v, numeric or k in {"default", "min", "max"})
            for k, v in expected.items())
    if isinstance(expected, list):
        return isinstance(actual, list) and len(actual) == len(expected) and all(
            manifests_match(a, b, numeric) for a, b in zip(actual, expected))
    if numeric and type(actual) in (int, float) and type(expected) in (int, float):
        return math.isclose(actual, expected, rel_tol=5e-7, abs_tol=1e-12)
    return type(actual) == type(expected) and actual == expected
