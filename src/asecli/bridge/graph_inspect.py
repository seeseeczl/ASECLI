"""Read editor-accurate ASE node bounds through MCP for visual layout checks."""

from __future__ import annotations

import json
import math
from pathlib import Path

from .backend import EditorExecutionError, extract_payload, run_editor_code
from .mcp_client import McpClient, McpError  # McpClient re-exported for test patching
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
    unity_instance: str | None = None,
    allow_remote_mcp: bool = False,
    backend: str = "auto",
    codely_port: int | None = None,
) -> dict[str, tuple[float, float, float, float]]:
    """Load a fresh hidden ASE window and return each node's runtime TruePosition."""
    path = Path(shader_path).resolve()
    if not path.exists():
        raise FileNotFoundError(shader_path)
    project_root = _detect_project_root(path)
    asset_path = path.as_posix().removeprefix(project_root.as_posix() + "/")
    envelope_text, used = run_editor_code(
        path,
        BOUNDS_SNIPPET.format(asset_path=json.dumps(asset_path)),
        backend=backend,
        mcp_url=mcp_url,
        instance_token=instance_token,
        allow_remote_mcp=allow_remote_mcp,
        codely_port=codely_port,
        unity_instance=unity_instance,
        mcp_factory=McpClient,
    )
    try:
        payload = extract_payload(envelope_text, used)
    except EditorExecutionError as exc:
        raise McpError(str(exc)) from exc
    if not payload.startswith("ASECLI_BOUNDS_V1\n"):
        raise McpError("node-bounds result has an unexpected payload")

    bounds: dict[str, tuple[float, float, float, float]] = {}
    for line in payload.splitlines()[1:]:
        if not line:
            continue
        parts = line.split("|")
        if len(parts) != 5:
            raise McpError("node-bounds result contains a malformed row")
        node_id = parts[0]
        try:
            rect = tuple(float(value) for value in parts[1:])
        except ValueError as exc:
            raise McpError("node-bounds result contains a non-numeric rectangle") from exc
        if not all(math.isfinite(value) for value in rect):
            raise McpError("node-bounds result contains a non-finite rectangle")
        if node_id in bounds:
            raise McpError(f"node-bounds result contains duplicate node id {node_id}")
        bounds[node_id] = rect  # type: ignore[assignment]
    if not bounds:
        raise McpError("node-bounds result is empty")
    return bounds
