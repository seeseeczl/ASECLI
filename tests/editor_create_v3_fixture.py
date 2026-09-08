"""Shared real-Editor fixture for EditorGraphSpec v3."""


def algorithm_spec(template_guid: str) -> dict:
    return {
        "version": 3,
        "primitives_version": 1,
        "template": {"guid": template_guid, "shader_name": "ASECLI/E2E/AlgorithmV3"},
        "nodes": [
            {"alias": "world", "kind": "primitive", "position": [-900, -120], "op": "world_position"},
            {
                "alias": "radius", "kind": "property", "type": "RangedFloatNode",
                "position": [-900, 120], "property_name": "_AuditRadius", "inspector_name": "验证半径",
                "tooltip": "验证 v3 数值范围、默认值和精度跨进程保持。", "parameter_type": "Property",
                "precision": "Half", "default": 0.5, "min": 0.0, "max": 2.0,
            },
            {
                "alias": "hardness", "kind": "property", "type": "RangedFloatNode",
                "position": [-900, 300], "property_name": "_AuditHardness", "inspector_name": "验证硬度",
                "tooltip": "验证 v3 原生 recipe 展开后的输入连接。", "parameter_type": "Property",
                "precision": "Float", "default": 0.25, "min": 0.0, "max": 1.0,
            },
            {
                "alias": "sphere", "kind": "recipe", "position": [-360, 20],
                "recipe": "sphere_mask",
                "code": "1 - saturate((distance(C, Center) - Radius) / (1 - Hardness))",
                "output_type": "FLOAT",
                "inputs": [
                    {"name": "C", "type": "FLOAT3"},
                    {"name": "Center", "type": "FLOAT3"},
                    {"name": "Radius", "type": "FLOAT"},
                    {"name": "Hardness", "type": "FLOAT"},
                ],
                "expansion": {
                    "primitives": [
                        {"id": "d", "op": "distance", "args": ["C", "Center"]},
                        {"id": "s", "op": "sub", "args": ["d", "Radius"]},
                        {"id": "h", "op": "one_minus", "args": ["Hardness"]},
                        {"id": "dv", "op": "div", "args": ["s", "h"]},
                        {"id": "sat", "op": "saturate", "args": ["dv"]},
                        {"id": "out", "op": "one_minus", "args": ["sat"]},
                    ],
                    "output": "out",
                },
            },
        ],
        "connections": [
            {"from": {"node": "world", "port": 0}, "to": {"node": "sphere", "port": 0}},
            {"from": {"node": "world", "port": 0}, "to": {"node": "sphere", "port": 1}},
            {"from": {"node": "radius", "port": 0}, "to": {"node": "sphere", "port": 2}},
            {"from": {"node": "hardness", "port": 0}, "to": {"node": "sphere", "port": 3}},
            {"from": {"node": "sphere", "port": 0}, "to": {"node": "master", "port": 3}},
        ],
    }


def algorithm_reload_method(template_guid: str) -> str:
    return '''    private static bool VerifyAlgorithm()
    {
        var previous = AmplifyShaderEditor.UIUtils.CurrentWindow;
        AmplifyShaderEditor.AmplifyShaderEditorWindow win = null;
        try
        {
            const string path = "Assets/ASECLIE2E/Generated/AlgorithmV3.shader";
            win = EditorWindow.CreateInstance<AmplifyShaderEditor.AmplifyShaderEditorWindow>();
            AmplifyShaderEditor.UIUtils.CurrentWindow = win;
            win.Show();
            var loaded = win.LoadFromDisk(path, null);
            if (loaded != AmplifyShaderEditor.ShaderLoadResult.LOADED &&
                loaded != AmplifyShaderEditor.ShaderLoadResult.TEMPLATE_LOADED) return false;
            var graph = win.CurrentGraph;
            var master = graph.CurrentMasterNode as AmplifyShaderEditor.TemplateMultiPassMasterNode;
            var shader = AssetDatabase.LoadAssetAtPath<Shader>(path);
            var world = graph.AllNodes.Find(n => n is AmplifyShaderEditor.WorldPosInputsNode);
            var radius = graph.AllNodes.Find(n => n is AmplifyShaderEditor.RangedFloatNode &&
                ((AmplifyShaderEditor.RangedFloatNode)n).PropertyName == "_AuditRadius") as AmplifyShaderEditor.RangedFloatNode;
            var hardness = graph.AllNodes.Find(n => n is AmplifyShaderEditor.RangedFloatNode &&
                ((AmplifyShaderEditor.RangedFloatNode)n).PropertyName == "_AuditHardness") as AmplifyShaderEditor.RangedFloatNode;
            var distance = graph.AllNodes.Find(n => n is AmplifyShaderEditor.DistanceOpNode);
            var subtract = graph.AllNodes.Find(n => n is AmplifyShaderEditor.SimpleSubtractOpNode);
            var divide = graph.AllNodes.Find(n => n is AmplifyShaderEditor.SimpleDivideOpNode);
            var saturate = graph.AllNodes.Find(n => n is AmplifyShaderEditor.SaturateNode);
            var oneMinus = graph.AllNodes.FindAll(n => n is AmplifyShaderEditor.OneMinusNode);
            var flags = System.Reflection.BindingFlags.Instance | System.Reflection.BindingFlags.NonPublic;
            var minField = typeof(AmplifyShaderEditor.RangedFloatNode).GetField("m_min", flags);
            var maxField = typeof(AmplifyShaderEditor.RangedFloatNode).GetField("m_max", flags);
            var precisionField = typeof(AmplifyShaderEditor.ParentNode).GetField("m_currentPrecisionType", flags);
            return master != null && master.CurrentTemplate != null && shader != null &&
                master.CurrentTemplate.GUID == "__TEMPLATE_GUID__" &&
                master.ShaderName == "ASECLI/E2E/AlgorithmV3" && shader.name == master.ShaderName &&
                world != null && radius != null && hardness != null && distance != null &&
                subtract != null && divide != null && saturate != null && oneMinus.Count == 2 &&
                System.Math.Abs(radius.Value - 0.5f) < 0.00001f &&
                System.Math.Abs((float)minField.GetValue(radius) - 0.0f) < 0.00001f &&
                System.Math.Abs((float)maxField.GetValue(radius) - 2.0f) < 0.00001f &&
                precisionField.GetValue(radius).ToString() == "Half" &&
                System.Math.Abs(hardness.Value - 0.25f) < 0.00001f &&
                System.Math.Abs((float)minField.GetValue(hardness) - 0.0f) < 0.00001f &&
                System.Math.Abs((float)maxField.GetValue(hardness) - 1.0f) < 0.00001f &&
                precisionField.GetValue(hardness).ToString() == "Float" &&
                graph.CurrentMasterNode.GetInputPortByUniqueId(3).IsConnected;
        }
        finally
        {
            AmplifyShaderEditor.UIUtils.CurrentWindow = previous;
            if (win != null) { win.Close(); Object.DestroyImmediate(win); }
        }
    }
'''.replace("__TEMPLATE_GUID__", template_guid)
