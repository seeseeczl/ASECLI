"""Read editor-accurate ASE node bounds through MCP for visual layout checks."""

from __future__ import annotations

import json
from pathlib import Path

from .mcp_client import McpClient, McpError, tool_text
from .recompile import _detect_project_root


BOUNDS_SNIPPET = r'''
string assetPath = {asset_path};
var shader = UnityEditor.AssetDatabase.LoadAssetAtPath<UnityEngine.Shader>(assetPath);
if (shader == null) throw new System.Exception("shader not found: " + assetPath);
var previousWindow = AmplifyShaderEditor.UIUtils.CurrentWindow;
var previousSelection = UnityEditor.Selection.activeObject;
AmplifyShaderEditor.AmplifyShaderEditorWindow win = null;
try
{{
    win = UnityEditor.EditorWindow.CreateInstance<AmplifyShaderEditor.AmplifyShaderEditorWindow>();
    AmplifyShaderEditor.UIUtils.CurrentWindow = win;
    var uiTextInfo = typeof(AmplifyShaderEditor.UIUtils).GetField(
        "m_textInfo",
        System.Reflection.BindingFlags.Static | System.Reflection.BindingFlags.NonPublic);
    if (uiTextInfo != null && uiTextInfo.GetValue(null) == null)
        uiTextInfo.SetValue(null, new System.Globalization.CultureInfo("en-US", false).TextInfo);

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
    var sb = new System.Text.StringBuilder("ASECLI_BOUNDS_V1\n");
    foreach (var node in win.CurrentGraph.AllNodes)
    {{
        var rect = node.TruePosition;
        sb.Append(node.UniqueId).Append('|')
          .Append(rect.x.ToString("R", System.Globalization.CultureInfo.InvariantCulture)).Append('|')
          .Append(rect.y.ToString("R", System.Globalization.CultureInfo.InvariantCulture)).Append('|')
          .Append(rect.width.ToString("R", System.Globalization.CultureInfo.InvariantCulture)).Append('|')
          .Append(rect.height.ToString("R", System.Globalization.CultureInfo.InvariantCulture)).Append('\n');
    }}
    return sb.ToString();
}}
finally
{{
    UnityEditor.Selection.activeObject = previousSelection;
    AmplifyShaderEditor.UIUtils.CurrentWindow = previousWindow;
    if (win != null)
    {{
        win.Close();
        UnityEngine.Object.DestroyImmediate(win);
    }}
}}
'''


def measure_node_bounds_via_mcp(
    shader_path: str,
    *,
    mcp_url: str = "http://127.0.0.1:8080/mcp",
    instance_token: str | None = None,
    allow_remote_mcp: bool = False,
) -> dict[str, tuple[float, float, float, float]]:
    """Load a fresh hidden ASE window and return each node's runtime TruePosition."""
    path = Path(shader_path).resolve()
    if not path.exists():
        raise FileNotFoundError(shader_path)
    project_root = _detect_project_root(path)
    asset_path = path.as_posix().removeprefix(project_root.as_posix() + "/")
    client = McpClient(
        mcp_url,
        instance_token=instance_token,
        allow_remote=allow_remote_mcp,
    )
    client.connect()
    result = client.call_tool(
        "execute_code",
        {"action": "execute", "code": BOUNDS_SNIPPET.format(asset_path=json.dumps(asset_path))},
    )
    envelope_text = tool_text(result, instance_token)
    try:
        envelope = json.loads(envelope_text)
        payload = envelope["data"]["result"]
    except (json.JSONDecodeError, KeyError, TypeError) as exc:
        raise McpError("MCP node-bounds result has an unexpected envelope") from exc
    if not isinstance(payload, str) or not payload.startswith("ASECLI_BOUNDS_V1\n"):
        raise McpError("MCP node-bounds result has an unexpected payload")

    bounds: dict[str, tuple[float, float, float, float]] = {}
    for line in payload.splitlines()[1:]:
        if not line:
            continue
        parts = line.split("|")
        if len(parts) != 5:
            raise McpError("MCP node-bounds result contains a malformed row")
        node_id = parts[0]
        try:
            rect = tuple(float(value) for value in parts[1:])
        except ValueError as exc:
            raise McpError("MCP node-bounds result contains a non-numeric rectangle") from exc
        if node_id in bounds:
            raise McpError(f"MCP node-bounds result contains duplicate node id {node_id}")
        bounds[node_id] = rect  # type: ignore[assignment]
    if not bounds:
        raise McpError("MCP node-bounds result is empty")
    return bounds
