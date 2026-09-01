"""Trigger ASE regeneration for a shader inside a running Unity/Tuanjie editor (TASK-0011)."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

from .mcp_client import McpClient, McpError, tool_text

RECOMPILE_SNIPPET = '''
string assetPath = {asset_path};
var shader = UnityEditor.AssetDatabase.LoadAssetAtPath<UnityEngine.Shader>(assetPath);
if (shader == null) throw new System.Exception("shader not found: " + assetPath);
var previousWindow = AmplifyShaderEditor.UIUtils.CurrentWindow;
var previousSelection = UnityEditor.Selection.activeObject;
AmplifyShaderEditor.AmplifyShaderEditorWindow win = null;
try
{
    win = UnityEditor.EditorWindow.CreateInstance<AmplifyShaderEditor.AmplifyShaderEditorWindow>();
    AmplifyShaderEditor.UIUtils.CurrentWindow = win;
    var uiTextInfo = typeof(AmplifyShaderEditor.UIUtils).GetField(
        "m_textInfo",
        System.Reflection.BindingFlags.Static | System.Reflection.BindingFlags.NonPublic);
    if (uiTextInfo != null && uiTextInfo.GetValue(null) == null)
        uiTextInfo.SetValue(null, new System.Globalization.CultureInfo("en-US", false).TextInfo);

    // CommentaryNode.Position reads Event.current. A direct hidden-window load
    // therefore fails outside OnGUI. Defer the asset and dispatch real GUI
    // events so ASE loads comment groups in its normal editor lifecycle.
    var delayedLoad = typeof(AmplifyShaderEditor.AmplifyShaderEditorWindow).GetField(
        "m_delayedLoadObject",
        System.Reflection.BindingFlags.Instance | System.Reflection.BindingFlags.NonPublic);
    if (delayedLoad == null)
        throw new System.Exception("ASE delayed-load field not found");
    delayedLoad.SetValue(win, shader);
    win.Show();

    var layoutEvent = new UnityEngine.Event();
    layoutEvent.type = UnityEngine.EventType.Layout;
    win.SendEvent(layoutEvent);
    var repaintEvent = new UnityEngine.Event();
    repaintEvent.type = UnityEngine.EventType.Repaint;
    win.SendEvent(repaintEvent);

    if (win.CurrentGraph == null || win.CurrentGraph.CurrentMasterNode == null)
        throw new System.Exception("ASE graph did not load in GUI event");
    bool saved = win.SaveToDisk(false);
    return "recompiled, saved=" + saved;
}
finally
{
    UnityEditor.Selection.activeObject = previousSelection;
    AmplifyShaderEditor.UIUtils.CurrentWindow = previousWindow;
    if (win != null)
    {
        win.Close();
        UnityEngine.Object.DestroyImmediate(win);
    }
}
'''


def recompile_via_mcp(
    shader_path: str,
    mcp_url: str = "http://127.0.0.1:8080/mcp",
    instance_token: str | None = None,
    allow_remote_mcp: bool = False,
) -> dict:
    """Open the shader in ASE inside the running editor and force save (regenerate HLSL)."""
    p = Path(shader_path).resolve()
    if not p.exists():
        raise FileNotFoundError(shader_path)
    before = hashlib.sha1(p.read_bytes()).hexdigest()
    project_root = _detect_project_root(p)
    asset_path = p.as_posix().removeprefix(project_root.as_posix() + "/")
    client = McpClient(mcp_url, instance_token=instance_token, allow_remote=allow_remote_mcp)
    client.connect()
    result = client.call_tool(
        "execute_code", {"action": "execute", "code": RECOMPILE_SNIPPET.replace("{asset_path}", json.dumps(asset_path))}
    )
    result_text = tool_text(result, instance_token)
    saved_match = re.search(r"\brecompiled,\s*saved=(true|false)\b", result_text, re.IGNORECASE)
    if not saved_match:
        raise McpError("MCP tool result did not confirm saved state")
    saved = saved_match.group(1).lower() == "true"
    if not saved:
        raise McpError("MCP tool did not confirm saved=True")
    after = hashlib.sha1(p.read_bytes()).hexdigest()
    return {
        "transport": "mcp",
        "server": mcp_url,
        "asset_path": asset_path,
        "saved": saved,
        "changed": before != after,
        "tool_result": "recompiled, saved=True",
    }


def _detect_project_root(shader_path: Path) -> Path:
    cur = shader_path.parent
    while cur != cur.parent:
        if (cur / "Assets").is_dir() and (cur / "ProjectSettings").is_dir():
            return cur
        cur = cur.parent
    raise ValueError(f"cannot locate Unity project root for {shader_path}")
