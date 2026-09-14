"""Preserve hidden material properties across native export."""
from asecli.core.model import parse_node_line

def test_hidden_shaderlab_property_remains_material_overridable():
    from asecli.sg_export.sources import property_spec

    node = parse_node_line(
        "Node;AmplifyShaderEditor.SamplerNode;68;0,0;Inherit;True;Property;"
        "_Tex;纹理;14;1;[HideInInspector];Create;False;0;0;0;True;0;False;-1;"
        "944392c2985544e1887f5223b229458a;944392c2985544e1887f5223b229458a;"
        "True;0;False;white;Auto;False;Object;-1;Auto;Texture2D"
    )
    compiled = {
        "_Tex": {
            "display_name": "纹理",
            "type": "texture2d",
            "default": None,
            "hdr": False,
            "exposed": False,
        }
    }

    result = property_spec(node, "texture2d", compiled, "Assets/laser.jpeg")

    assert result["exposed"] is True
    assert result["settings"] == {"hidden": True}


def test_runtime_property_data_roundtrips_and_mutations_are_detected():
    from copy import deepcopy
    from asecli.sg_export.sources import compiled_properties
    from asecli.sg_export.reconciliation import reconcile_shaderlab_properties

    compiled = compiled_properties('_Gain("增益", Range(-2, 8)) = 0.375\n')
    baseline = {"name": "_Gain", "type": "float", "default": 0.375,
                "range": [-2.0, 8.0], "exposed": True}
    report, diagnostics = {"mappings": []}, []
    reconcile_shaderlab_properties(compiled, [baseline], report, diagnostics)
    assert diagnostics == []
    for field, value in [("name", "_Renamed"), ("type", "vector4"),
                         ("default", 1.0), ("range", [-1, 8]), ("range", [-2, 9]),
                         ("exposed", False), ("settings", {"hidden": True})]:
        changed = deepcopy(baseline)
        changed[field] = value
        diagnostics = []
        reconcile_shaderlab_properties(compiled, [changed], {"mappings": []}, diagnostics)
        assert any(d["code"] == "PROPERTY_FIDELITY_MISMATCH" for d in diagnostics), field


def test_keyword_attribute_cannot_be_silently_dropped():
    from asecli.sg_export.sources import compiled_properties
    from asecli.sg_export.reconciliation import reconcile_shaderlab_properties

    compiled = compiled_properties('[Toggle(FEATURE_ON)] _Feature("功能", Float) = 1\n')
    diagnostics = []
    reconcile_shaderlab_properties(compiled, [
        {"name": "_Feature", "type": "float", "default": 1.0, "exposed": True}
    ], {"mappings": []}, diagnostics)
    assert diagnostics[0]["code"] == "PROPERTY_ATTRIBUTE_UNSUPPORTED"
    assert diagnostics[0]["reason"]["attribute"] == "Toggle(FEATURE_ON)"
