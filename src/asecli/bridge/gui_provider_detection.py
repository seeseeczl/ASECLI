"""Static and Editor-runtime detection of the native MZGUI material provider."""

from __future__ import annotations

import json
from pathlib import Path
import re

from .mcp_client import McpClient, McpError, tool_text


_NATIVE_NAMESPACE_RE = re.compile(r"\bnamespace\s+MZGUI\b")
_NATIVE_GUI_BASE_RE = re.compile(r"\bclass\s+MZGUI\s*:\s*([A-Za-z_][A-Za-z0-9_:.]*)")
_SHADER_GUI_ALIAS_RE = re.compile(
    r"\busing\s+([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(?:global::)?UnityEditor\.ShaderGUI\s*;"
)
_GUI_PROBE_MARKER = "ASECLI_GUI_SUPPORT_PROBE_V1:"
GUI_SUPPORT_PROBE_SNIPPET = r'''
var probe = new Newtonsoft.Json.Linq.JObject();
probe["protocol"] = "ASECLI_GUI_SUPPORT_PROBE_V1";
probe["assets_path"] = System.IO.Path.GetFullPath(UnityEngine.Application.dataPath);
System.Type mzguiType = null;
foreach (var assembly in System.AppDomain.CurrentDomain.GetAssemblies())
{
    var candidate = assembly.GetType("MZGUI.MZGUI", false);
    if (candidate != null) { mzguiType = candidate; break; }
}
probe["type_found"] = mzguiType != null;
probe["detected"] = mzguiType != null && typeof(UnityEditor.ShaderGUI).IsAssignableFrom(mzguiType);
probe["assembly"] = mzguiType == null ? null : mzguiType.Assembly.FullName;
return "ASECLI_GUI_SUPPORT_PROBE_V1:" + probe.ToString(Newtonsoft.Json.Formatting.None);
'''.strip()


def probe_native_mzgui_for_assets(
    project_assets: Path,
    *,
    mcp_url: str,
    instance_token: str | None,
    allow_remote_mcp: bool,
) -> dict:
    client = McpClient(mcp_url, instance_token=instance_token, allow_remote=allow_remote_mcp)
    client.connect()
    result = client.call_tool("execute_code", {"action": "execute", "code": GUI_SUPPORT_PROBE_SNIPPET})
    text = tool_text(result, instance_token)
    marker = text.find(_GUI_PROBE_MARKER)
    if marker < 0:
        raise McpError("MCP tool result did not contain the GUI support probe marker")
    raw = text[marker + len(_GUI_PROBE_MARKER) :].lstrip()
    try:
        value, _ = json.JSONDecoder().raw_decode(raw)
    except json.JSONDecodeError as exc:
        raise McpError("MCP GUI support probe returned malformed JSON") from exc
    if not isinstance(value, dict):
        raise McpError("MCP GUI support probe result must be an object")
    validate_runtime_probe(value, project_assets)
    return value


def validate_runtime_probe(probe: dict, project_assets: Path) -> None:
    if probe.get("protocol") != "ASECLI_GUI_SUPPORT_PROBE_V1":
        raise ValueError("GUI support runtime probe protocol is missing or unsupported")
    if not isinstance(probe.get("detected"), bool) or not isinstance(probe.get("type_found"), bool):
        raise ValueError("GUI support runtime probe booleans are invalid")
    assets_path = probe.get("assets_path")
    if not isinstance(assets_path, str) or Path(assets_path).resolve() != project_assets.resolve():
        raise ValueError("connected Editor project does not match the requested project root")


def scan_native_mzgui(project_root: Path, *, skip_source_name: str) -> tuple[list[str], list[str]]:
    search_roots = [project_root / "Assets", project_root / "Packages"]
    package_cache = project_root / "Library" / "PackageCache"
    if package_cache.is_dir():
        try:
            search_roots.extend(entry for entry in package_cache.iterdir() if "mzgui" in entry.name.lower())
        except OSError:
            pass

    evidence: list[str] = []
    candidates: list[str] = []
    for root in search_roots:
        if not root.is_dir():
            continue
        for source in root.rglob("*.cs"):
            if source.name == skip_source_name:
                continue
            try:
                if source.stat().st_size > 2_000_000:
                    continue
                text = source.read_text(encoding="utf-8-sig", errors="ignore")
            except OSError:
                continue
            relative = _relative_evidence(source, project_root)
            if _source_defines_native_mzgui(text):
                evidence.append(relative)
            elif _NATIVE_NAMESPACE_RE.search(text) and re.search(r"\bclass\s+MZGUI\b", text):
                candidates.append(relative)
        for assembly in root.rglob("*.dll"):
            try:
                if assembly.stat().st_size > 100_000_000:
                    continue
                data = assembly.read_bytes()
            except OSError:
                continue
            if "mzgui" in assembly.name.lower() or (b"MZGUI" in data and b"ShaderGUI" in data):
                candidates.append(_relative_evidence(assembly, project_root))

    for manifest_name in ("manifest.json", "packages-lock.json"):
        manifest = project_root / "Packages" / manifest_name
        if not manifest.is_file():
            continue
        try:
            if "mzgui" in manifest.read_text(encoding="utf-8", errors="ignore").lower():
                candidates.append(_relative_evidence(manifest, project_root))
        except OSError:
            continue
    return sorted(set(evidence)), sorted(set(candidates) - set(evidence))


def _source_defines_native_mzgui(text: str) -> bool:
    if not _NATIVE_NAMESPACE_RE.search(text):
        return False
    match = _NATIVE_GUI_BASE_RE.search(text)
    if match is None:
        return False
    base = match.group(1).replace("global::", "")
    if base in {"ShaderGUI", "UnityEditor.ShaderGUI"}:
        return True
    aliases = {alias.group(1) for alias in _SHADER_GUI_ALIAS_RE.finditer(text)}
    return base in aliases


def _relative_evidence(path: Path, project_root: Path) -> str:
    try:
        return path.resolve().relative_to(project_root).as_posix()
    except ValueError:
        return str(path.resolve())
