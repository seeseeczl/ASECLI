"""Trigger ASE regeneration for a shader inside a running Unity/Tuanjie editor (TASK-0011)."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from .mcp_client import McpClient

RECOMPILE_SNIPPET = '''
string assetPath = {asset_path};
var shader = UnityEditor.AssetDatabase.LoadAssetAtPath<UnityEngine.Shader>(assetPath);
if (shader == null) throw new System.Exception("shader not found: " + assetPath);
var win = UnityEditor.EditorWindow.CreateInstance<AmplifyShaderEditor.AmplifyShaderEditorWindow>();
AmplifyShaderEditor.UIUtils.CurrentWindow = win;
win.LoadObject(shader);
bool saved = win.SaveToDisk(false);
UnityEngine.Object.DestroyImmediate(win);
return "recompiled, saved=" + saved;
'''


def recompile_via_mcp(
    shader_path: str,
    mcp_url: str = "http://127.0.0.1:8080/mcp",
    instance_token: str | None = None,
) -> dict:
    """Open the shader in ASE inside the running editor and force save (regenerate HLSL)."""
    p = Path(shader_path).resolve()
    if not p.exists():
        raise FileNotFoundError(shader_path)
    before = hashlib.sha1(p.read_bytes()).hexdigest()
    project_root = _detect_project_root(p)
    asset_path = p.as_posix().removeprefix(project_root.as_posix() + "/")
    client = McpClient(mcp_url, instance_token=instance_token)
    client.connect()
    result = client.call_tool(
        "execute_code", {"action": "execute", "code": RECOMPILE_SNIPPET.format(asset_path=json.dumps(asset_path))}
    )
    after = hashlib.sha1(p.read_bytes()).hexdigest()
    return {
        "transport": "mcp",
        "server": mcp_url,
        "asset_path": asset_path,
        "changed": before != after,
        "tool_result": result,
    }


def _detect_project_root(shader_path: Path) -> Path:
    cur = shader_path.parent
    while cur != cur.parent:
        if (cur / "Assets").is_dir() and (cur / "ProjectSettings").is_dir():
            return cur
        cur = cur.parent
    raise ValueError(f"cannot locate Unity project root for {shader_path}")
