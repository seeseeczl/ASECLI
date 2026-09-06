"""Editor-accurate node, title, and port geometry for meticulous layout."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path

from .mcp_client import McpClient, McpError, tool_text
from .recompile import _detect_project_root
from .graph_geometry_parser import parse_geometry_payload


GEOMETRY_SNIPPET = r'''
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
    var flags = System.Reflection.BindingFlags.Instance | System.Reflection.BindingFlags.Public |
                System.Reflection.BindingFlags.NonPublic;
    System.Func<System.Type, string, System.Reflection.MemberInfo> findMember = (type, name) =>
    {{
        while (type != null)
        {{
            var property = type.GetProperty(name, flags);
            if (property != null) return property;
            var field = type.GetField(name, flags);
            if (field != null) return field;
            type = type.BaseType;
        }}
        return null;
    }};
    System.Func<System.Reflection.MemberInfo, object, object> readMember = (member, owner) =>
    {{
        if (member is System.Reflection.PropertyInfo)
            return ((System.Reflection.PropertyInfo)member).GetValue(owner, null);
        if (member is System.Reflection.FieldInfo)
            return ((System.Reflection.FieldInfo)member).GetValue(owner);
        return null;
    }};
    System.Func<object, string> displayText = value =>
    {{
        if (value == null) return "";
        if (value is UnityEngine.GUIContent) return ((UnityEngine.GUIContent)value).text ?? "";
        return value.ToString() ?? "";
    }};
    System.Func<string, string> encodeText = value => System.Convert.ToBase64String(
        System.Text.Encoding.UTF8.GetBytes(value ?? ""));
    var uiTextInfo = typeof(AmplifyShaderEditor.UIUtils).GetField(
        "m_textInfo", System.Reflection.BindingFlags.Static | System.Reflection.BindingFlags.NonPublic);
    if (uiTextInfo != null && uiTextInfo.GetValue(null) == null)
        uiTextInfo.SetValue(null, new System.Globalization.CultureInfo("en-US", false).TextInfo);
    var delayedLoad = typeof(AmplifyShaderEditor.AmplifyShaderEditorWindow).GetField(
        "m_delayedLoadObject", System.Reflection.BindingFlags.Instance | System.Reflection.BindingFlags.NonPublic);
    if (delayedLoad == null) throw new System.Exception("ASE delayed-load field not found");
    delayedLoad.SetValue(win, shader);
    win.Show();
    var layoutEvent = new UnityEngine.Event(); layoutEvent.type = UnityEngine.EventType.Layout;
    win.SendEvent(layoutEvent);
    var repaintEvent = new UnityEngine.Event(); repaintEvent.type = UnityEngine.EventType.Repaint;
    win.SendEvent(repaintEvent);
    if (win.CurrentGraph == null || win.CurrentGraph.CurrentMasterNode == null)
        throw new System.Exception("ASE graph did not load in GUI event");

    // ASE only fills TruePosition size, HeaderPosition and port rectangles
    // while a node participates in a layout pass. Large graphs leave
    // off-screen nodes unmeasured, so run one non-drawing, all-visible layout
    // pass in the temporary window before collecting geometry.
    var probeDraw = win.CameraDrawInfo;
    if (probeDraw == null)
        throw new System.Exception("ASE camera draw-info is unavailable");
    // ParentNode visibility compares against CameraArea width/height and does
    // not use its x/y origin, so translate graph coordinates into the positive
    // probe viewport instead of using a negative-origin rectangle.
    probeDraw.CameraArea = new UnityEngine.Rect(0f, 0f, 20000000f, 20000000f);
    probeDraw.TransformedCameraArea = probeDraw.CameraArea;
    probeDraw.CameraOffset = new UnityEngine.Vector2(10000000f, 10000000f);
    probeDraw.InvertedZoom = 1f;
    probeDraw.CurrentEventType = UnityEngine.EventType.Repaint;
    foreach (var probeNode in win.CurrentGraph.AllNodes)
    {{
        probeNode.OnNodeLogicUpdate(probeDraw);
        probeNode.OnNodeLayout(probeDraw);
    }}

    var inv = System.Globalization.CultureInfo.InvariantCulture;
    var sb = new System.Text.StringBuilder("ASECLI_GEOMETRY_V3\n");
    foreach (var node in win.CurrentGraph.AllNodes)
    {{
        var rect = node.TruePosition;
        // Template multi-pass graphs keep dormant master placeholders whose
        // editor rect is intentionally empty. They are not part of the
        // currently drawable graph and are omitted from the geometry payload.
        if (rect.width <= 0 || rect.height <= 0) continue;
        var global = node.GlobalPosition;
        var scaleX = global.width / rect.width;
        var scaleY = global.height / rect.height;
        if (scaleX <= 0 || scaleY <= 0)
            throw new System.Exception("ASE node coordinate transform unavailable for node " + node.UniqueId);
        var nodeType = node.GetType();
        var titleMember = findMember(nodeType, "TitleContent") ?? findMember(nodeType, "m_content") ??
                          findMember(nodeType, "Title") ?? findMember(nodeType, "m_title");
        string nodeTitle = displayText(readMember(titleMember, node));
        var headerMember = findMember(nodeType, "HeaderPosition") ?? findMember(nodeType, "m_headerPosition");
        object headerValue = headerMember is System.Reflection.PropertyInfo
            ? ((System.Reflection.PropertyInfo)headerMember).GetValue(node, null)
            : headerMember is System.Reflection.FieldInfo
                ? ((System.Reflection.FieldInfo)headerMember).GetValue(node) : null;
        if (!(headerValue is UnityEngine.Rect))
            throw new System.Exception("ASE node header geometry unavailable for node " + node.UniqueId);
        var header = (UnityEngine.Rect)headerValue;
        sb.Append("N|").Append(node.UniqueId).Append('|')
          .Append(rect.x.ToString("R", inv)).Append('|').Append(rect.y.ToString("R", inv)).Append('|')
          .Append(rect.width.ToString("R", inv)).Append('|').Append(rect.height.ToString("R", inv)).Append('|')
          .Append((header.height / scaleY).ToString("R", inv)).Append('|')
          .Append(encodeText(nodeTitle)).Append('\n');
        foreach (var port in node.InputPorts)
        {{
            var portType = port.GetType();
            var idMember = findMember(portType, "PortId") ?? findMember(portType, "UniqueId") ??
                           findMember(portType, "m_portId");
            var posMember = findMember(portType, "Position") ?? findMember(portType, "PortPosition") ??
                            findMember(portType, "m_position");
            var nameMember = findMember(portType, "Name") ?? findMember(portType, "m_name");
            object idValue = idMember is System.Reflection.PropertyInfo
                ? ((System.Reflection.PropertyInfo)idMember).GetValue(port, null)
                : idMember is System.Reflection.FieldInfo ? ((System.Reflection.FieldInfo)idMember).GetValue(port) : null;
            object posValue = posMember is System.Reflection.PropertyInfo
                ? ((System.Reflection.PropertyInfo)posMember).GetValue(port, null)
                : posMember is System.Reflection.FieldInfo ? ((System.Reflection.FieldInfo)posMember).GetValue(port) : null;
            if (idValue == null || (!(posValue is UnityEngine.Rect) && !(posValue is UnityEngine.Vector2)))
                throw new System.Exception("ASE input-port geometry unavailable for node " + node.UniqueId);
            if (posValue is UnityEngine.Rect && (((UnityEngine.Rect)posValue).width <= 0 || ((UnityEngine.Rect)posValue).height <= 0))
                continue;
            if (posValue is UnityEngine.Vector2 && ((UnityEngine.Vector2)posValue) == UnityEngine.Vector2.zero)
                continue;
            var screenCenter = posValue is UnityEngine.Rect ? ((UnityEngine.Rect)posValue).center : (UnityEngine.Vector2)posValue;
            string portName = displayText(readMember(nameMember, port));
            var portCenter = new UnityEngine.Vector2(
                rect.x + (screenCenter.x - global.x) / scaleX,
                rect.y + (screenCenter.y - global.y) / scaleY);
            sb.Append("I|").Append(node.UniqueId).Append('|').Append(idValue).Append('|')
              .Append(portCenter.x.ToString("R", inv)).Append('|')
              .Append(portCenter.y.ToString("R", inv)).Append('|')
              .Append(encodeText(portName)).Append('\n');
        }}
        foreach (var port in node.OutputPorts)
        {{
            var portType = port.GetType();
            var idMember = findMember(portType, "PortId") ?? findMember(portType, "UniqueId") ??
                           findMember(portType, "m_portId");
            var posMember = findMember(portType, "Position") ?? findMember(portType, "PortPosition") ??
                            findMember(portType, "m_position");
            var nameMember = findMember(portType, "Name") ?? findMember(portType, "m_name");
            object idValue = idMember is System.Reflection.PropertyInfo
                ? ((System.Reflection.PropertyInfo)idMember).GetValue(port, null)
                : idMember is System.Reflection.FieldInfo ? ((System.Reflection.FieldInfo)idMember).GetValue(port) : null;
            object posValue = posMember is System.Reflection.PropertyInfo
                ? ((System.Reflection.PropertyInfo)posMember).GetValue(port, null)
                : posMember is System.Reflection.FieldInfo ? ((System.Reflection.FieldInfo)posMember).GetValue(port) : null;
            if (idValue == null || (!(posValue is UnityEngine.Rect) && !(posValue is UnityEngine.Vector2)))
                throw new System.Exception("ASE output-port geometry unavailable for node " + node.UniqueId);
            if (posValue is UnityEngine.Rect && (((UnityEngine.Rect)posValue).width <= 0 || ((UnityEngine.Rect)posValue).height <= 0))
                continue;
            if (posValue is UnityEngine.Vector2 && ((UnityEngine.Vector2)posValue) == UnityEngine.Vector2.zero)
                continue;
            var screenCenter = posValue is UnityEngine.Rect ? ((UnityEngine.Rect)posValue).center : (UnityEngine.Vector2)posValue;
            string portName = displayText(readMember(nameMember, port));
            var portCenter = new UnityEngine.Vector2(
                rect.x + (screenCenter.x - global.x) / scaleX,
                rect.y + (screenCenter.y - global.y) / scaleY);
            sb.Append("O|").Append(node.UniqueId).Append('|').Append(idValue).Append('|')
              .Append(portCenter.x.ToString("R", inv)).Append('|')
              .Append(portCenter.y.ToString("R", inv)).Append('|')
              .Append(encodeText(portName)).Append('\n');
        }}
    }}
    return sb.ToString();
}}
finally
{{
    UnityEditor.Selection.activeObject = previousSelection;
    AmplifyShaderEditor.UIUtils.CurrentWindow = previousWindow;
    if (win != null) {{ win.Close(); UnityEngine.Object.DestroyImmediate(win); }}
}}
'''


@dataclass(frozen=True)
class EditorNodeGeometry:
    x: float
    y: float
    width: float
    height: float
    title_height: float
    input_ports: dict[str, tuple[float, float]]
    output_ports: dict[str, tuple[float, float]]
    node_title: str = ""
    input_port_labels: dict[str, str] | None = None
    output_port_labels: dict[str, str] | None = None


def inspect_graph_geometry_via_mcp(
    shader_path: str, *, mcp_url: str = "http://127.0.0.1:8080/mcp",
    instance_token: str | None = None, unity_instance: str | None = None,
    allow_remote_mcp: bool = False,
) -> dict[str, EditorNodeGeometry]:
    path = Path(shader_path).resolve()
    if not path.exists():
        raise FileNotFoundError(shader_path)
    root = _detect_project_root(path)
    asset_path = path.as_posix().removeprefix(root.as_posix() + "/")
    client = McpClient(mcp_url, instance_token=instance_token, allow_remote=allow_remote_mcp)
    client.connect()
    args = {"action": "execute", "code": GEOMETRY_SNIPPET.format(asset_path=json.dumps(asset_path))}
    if unity_instance is not None:
        args["unity_instance"] = unity_instance
    envelope_text = tool_text(client.call_tool("execute_code", args), instance_token)
    try:
        envelope = json.loads(envelope_text)
    except json.JSONDecodeError as exc:
        raise McpError("MCP graph-geometry result has an unexpected envelope") from exc
    if not isinstance(envelope, dict):
        raise McpError("MCP graph-geometry result has an unexpected envelope")
    if envelope.get("success") is False:
        data = envelope.get("data") if isinstance(envelope.get("data"), dict) else {}
        detail = envelope.get("message") or data.get("reason") or "Unity execution failed"
        available = data.get("available_instances")
        if isinstance(available, list) and available:
            detail = f"{detail}; available instances: {', '.join(str(item) for item in available)}"
        raise McpError(str(detail), data=data)
    try:
        payload = envelope["data"]["result"]
    except (KeyError, TypeError) as exc:
        raise McpError("MCP graph-geometry result has an unexpected envelope") from exc
    if not isinstance(payload, str) or not payload.startswith(("ASECLI_GEOMETRY_V2\n", "ASECLI_GEOMETRY_V3\n")):
        raise McpError("MCP graph-geometry result has an unexpected payload")
    return parse_geometry_payload(payload, EditorNodeGeometry)


def _parse_geometry_payload(payload: str) -> dict[str, EditorNodeGeometry]:
    """Compatibility wrapper retained for focused parser tests/importers."""
    return parse_geometry_payload(payload, EditorNodeGeometry)
