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
