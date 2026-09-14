"""ASE parser-to-native-spec integration for surface semantic lowering."""

from pathlib import Path

import pytest

from asecli.export_sg import ExportError, URP_UNLIT_GUID, bind_named_ports, build_candidate
from asecli.schema import schema_for


def _node(kind, node_id):
    schema=schema_for(kind);assert schema
    return ["Node",kind,str(node_id),"0,0","Inherit","False",*schema["fields"]]


def _master():
    return ["Node","AmplifyShaderEditor.TemplateMultiPassMasterNode","1","0,0","Float","False","True","-1","2","UnityEditor.ShaderGraphUnlitGUI","0","1","Test",URP_UNLIT_GUID,"True","Forward","UniversalMaterialType=Unlit","RenderType=Transparent","Standard","3","Surface","1","0","  Blend","3","0","Two Sided","1","0","Forward Only","0","0","Cast Shadows","1","0","  Use Shadow Threshold","0","0","Receive Shadows","1","0","GPU Instancing","1","0","LOD CrossFade","0","0","Built-in Fog","1","0","Extra Pre Pass","0","0","Tessellation","0","0"]


def _shader(nodes,wires,pass_body="Cull Back\nBlend DstColor Zero, Zero One"):
    rows="\n".join(";".join(row) for row in nodes)
    return f'Shader "Test"\n{{\nProperties{{}}\nSubShader{{Pass{{\nName "Forward"\n{pass_body}\nHLSLPROGRAM\nENDHLSL\n}}}}\n}}\n/*ASEBEGIN\nVersion=19109\n{rows}\n'+"\n".join(wires)+"\nASEEND*/\n//CHKSM=TEST\n"


def _project(tmp_path):
    (tmp_path/"Assets").mkdir();(tmp_path/"ProjectSettings").mkdir();return tmp_path


def test_parser_candidate_folds_explicit_alpha_modulate(tmp_path: Path):
    project=_project(tmp_path)
    modulate=("Node;AmplifyShaderEditor.CustomExpressionNode;146;0,0;Inherit;False;lerp(float3(1,1,1), C, A);3;Create;2;True;C;FLOAT3;0,0,0;In;;Inherit;False;True;A;FLOAT;0;In;;Inherit;False;AlphaModulate;True;False;0;;False;2;0;FLOAT3;0,0,0;False;1;FLOAT;0;False;1;FLOAT3;0").split(";")
    source=project/"Assets"/"multiply.shader"
    modulate[4] = "Half"
    modulate[6] = "lerp(half3(1,1,1), C, A)"
    source.write_text(_shader([_node("AmplifyShaderEditor.Vector3Node",10),_node("AmplifyShaderEditor.RangedFloatNode",20),modulate,_master()],["WireConnection;146;0;10;0","WireConnection;146;1;20;0","WireConnection;1;2;146;0","WireConnection;1;3;20;0"]),encoding="utf-8")
    candidate,report,nodes,edges=build_candidate(source,project)
    result=bind_named_ports(candidate,report,nodes,edges)
    assert not any(n.get("function",{}).get("name")=="ASEExpression_146" for n in result["nodes"])
    assert [e for e in result["connections"] if e["to"][0]=="SurfaceDescription.BaseColor"]==[{"from":["ase_10","Out"],"to":["SurfaceDescription.BaseColor","Base Color"]}]


def test_independent_alpha_blend_fails_closed(tmp_path: Path):
    project=_project(tmp_path);source=project/"Assets"/"alpha.shader"
    source.write_text(_shader([_node("AmplifyShaderEditor.RangedFloatNode",10),_master()],["WireConnection;1;2;10;0","WireConnection;1;3;10;0"],"Blend DstColor Zero, One One"),encoding="utf-8")
    with pytest.raises(ExportError) as raised:build_candidate(source,project)
    issue=next(x for x in raised.value.report["diagnostics"] if x["code"]=="ALPHA_BLEND_UNREPRESENTABLE")
    assert issue["reason"]["source"]["alpha"]==["One","One"]


def test_source_alpha_multiply_selects_exact_target(tmp_path: Path):
    project=_project(tmp_path);source=project/"Assets"/"exact.shader"
    source.write_text(_shader([_node("AmplifyShaderEditor.RangedFloatNode",10),_master()],
        ["WireConnection;1;2;10;0","WireConnection;1;3;10;0"],
        "Blend DstColor Zero, One Zero"),encoding="utf-8")
    candidate,report,nodes,edges=build_candidate(source,project)
    result=bind_named_ports(candidate,report,nodes,edges)
    assert result["target"]["blend"] == "MultiplySourceAlpha"
    assert report["surface_semantics"]["alpha_modulate_strategy"] == "preserve_graph_float_expression"
