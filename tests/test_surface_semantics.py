"""Target-aware ASE -> Shader Graph surface semantic rewrites."""

from __future__ import annotations

import pytest

from asecli.sg_export.model import SemanticEdge, SemanticNode
from asecli.sg_export.surface_semantics import normalize_surface_outputs


def _node(
    body: str = "Out = lerp(float3(1,1,1), C, A);", output_name: str = "Out"
) -> SemanticNode:
    return SemanticNode(
        source_id="146",
        target_id="ase_146",
        target_type="custom-function",
        position=[0.0, 0.0],
        input_names={0: "C", 1: "A"},
        output_names={0: output_name},
        function={
            "name": "ASEExpression_146",
            "source": "String",
            "body": body,
            "ports": [
                {"name": output_name, "type": "Vector3", "direction": "Output"},
                {"name": "C", "type": "Vector3", "direction": "Input"},
                {"name": "A", "type": "Vector1", "direction": "Input"},
            ],
        },
    )


def _edges(alpha_source: str = "alpha") -> list[SemanticEdge]:
    return [
        SemanticEdge("color", 0, "ase_146", -1),
        SemanticEdge("alpha", 0, "ase_146", -2),
        SemanticEdge("ase_146", 0, "SurfaceDescription.BaseColor", 0),
        SemanticEdge(alpha_source, 0, "SurfaceDescription.Alpha", 0),
    ]


def _normalize(
    *, body: str = "Out = lerp(float3(1,1,1), C, A);",
    alpha_source: str = "alpha",
    blend: str = "Multiply",
    extra_edges: list[SemanticEdge] | None = None,
    source_text: str | None = 'Pass { Name "Forward"\nBlend DstColor Zero, Zero One\nHLSLPROGRAM\nENDHLSL\n}',
    output_name: str = "Out",
):
    node = _node(body, output_name)
    nodes = [node]
    edges = _edges(alpha_source) + list(extra_edges or [])
    mappings = {"146": {0: ("ase_146", 0), -1: ("ase_146", -1), -2: ("ase_146", -2)}}
    report = {
        "diagnostics": [],
        "mappings": [{"source_nodes": ["146"], "target_nodes": ["ase_146"], "kind": "direct"}]
    }
    result = normalize_surface_outputs(
        nodes,
        edges,
        {"surface": "Transparent", "blend": blend},
        mappings,
        report,
        source_text,
    )
    return result, mappings, report


@pytest.mark.parametrize(
    "white",
    ["float3(1,1,1)", "float3(1.0, 1.00, 1.000f)", "half3(1,1,1)", "(1.0).xxx"],
)
def test_multiply_folds_explicit_alpha_modulate_with_same_alpha(white: str):
    (nodes, edges), mappings, report = _normalize(
        body=f"Out = lerp({white}, C, A);"
    )

    assert nodes == []
    assert mappings == {}
    assert SemanticEdge("color", 0, "SurfaceDescription.BaseColor", 0) in edges
    assert SemanticEdge("alpha", 0, "SurfaceDescription.Alpha", 0) in edges
    assert not any(edge.source_id == "ase_146" or edge.target_id == "ase_146" for edge in edges)
    rewrite = report["surface_semantics"]["rewrites"][0]
    assert rewrite["rule"] == "SEM-BLEND-001"
    assert rewrite["source_modulation_count"] == 1
    assert rewrite["target_modulation_count"] == 1
    assert rewrite["removed"] is True


def test_different_surface_alpha_does_not_fold():
    (nodes, edges), mappings, report = _normalize(alpha_source="other_alpha")

    assert [node.target_id for node in nodes] == ["ase_146"]
    assert edges == _edges("other_alpha")
    assert "146" in mappings
    assert report["surface_semantics"]["rewrites"] == []
    assert report["diagnostics"][0]["code"] == "DUPLICATE_ALPHA_MODULATE_UNRESOLVED"


def test_non_multiply_target_does_not_fold():
    (nodes, edges), _, report = _normalize(blend="Alpha")

    assert [node.target_id for node in nodes] == ["ase_146"]
    assert edges == _edges()
    assert report["surface_semantics"]["target_pipeline"]["implicit_alpha_modulate"] is False


def test_non_white_lerp_does_not_fold():
    (nodes, edges), _, report = _normalize(body="Out = lerp(float3(0.5,0.5,0.5), C, A);")

    assert [node.target_id for node in nodes] == ["ase_146"]
    assert edges == _edges()
    assert report["surface_semantics"]["rewrites"] == []


@pytest.mark.parametrize(
    ("body", "output_name"),
    [
        ("Out = lerp(float3(1,1,1), C, A); // exact modulation", "Out"),
        ("Result = lerp(float3(1,1,1), C, A);", "Result"),
        ("/* prefix */ Out = lerp(float3(1,1,1), C, A);", "Out"),
    ],
)
def test_equivalent_alpha_modulate_syntax_is_folded(body: str, output_name: str):
    (nodes, edges), _, report = _normalize(body=body, output_name=output_name)

    assert nodes == []
    assert SemanticEdge("color", 0, "SurfaceDescription.BaseColor", 0) in edges
    assert report["surface_semantics"]["rewrites"][0]["matcher_version"] == 4


def test_unproven_base_color_custom_function_fails_closed():
    (nodes, edges), _, report = _normalize(body="Out = UnknownColorTransform(C, A);")

    assert [node.target_id for node in nodes] == ["ase_146"]
    assert edges == _edges()
    assert report["diagnostics"][0]["code"] == "ALPHA_MODULATE_UNPROVEN"


def test_upstream_alpha_modulate_behind_passthrough_fails_closed():
    modulate = _node()
    passthrough = SemanticNode(
        source_id="147",
        target_id="ase_147",
        target_type="reroute",
        position=[100.0, 0.0],
        input_names={0: "In"},
        output_names={0: "Out"},
    )
    nodes = [modulate, passthrough]
    edges = [
        SemanticEdge("color", 0, "ase_146", -1),
        SemanticEdge("alpha", 0, "ase_146", -2),
        SemanticEdge("ase_146", 0, "ase_147", -1),
        SemanticEdge("ase_147", 0, "SurfaceDescription.BaseColor", 0),
        SemanticEdge("alpha", 0, "SurfaceDescription.Alpha", 0),
    ]
    mappings = {
        "146": {0: ("ase_146", 0), -1: ("ase_146", -1), -2: ("ase_146", -2)},
        "147": {0: ("ase_147", 0), -1: ("ase_147", -1)},
    }
    report = {"diagnostics": [], "mappings": []}

    result_nodes, result_edges = normalize_surface_outputs(
        nodes,
        edges,
        {"surface": "Transparent", "blend": "Multiply"},
        mappings,
        report,
        'Pass {\nName "Forward"\nBlend DstColor Zero, Zero One\nHLSLPROGRAM\nENDHLSL\n}',
    )

    assert result_nodes == nodes
    assert result_edges == edges
    assert report["diagnostics"][0]["code"] == "DUPLICATE_ALPHA_MODULATE_UNRESOLVED"
    assert report["surface_semantics"]["unresolved"]["source_node"] == "146"


def test_unproved_upstream_custom_function_fails_closed():
    custom = _node(body="Out = UnknownColorTransform(C, A);")
    passthrough = SemanticNode(
        source_id="147",
        target_id="ase_147",
        target_type="reroute",
        position=[100.0, 0.0],
        input_names={0: "In"},
        output_names={0: "Out"},
    )
    edges = [
        SemanticEdge("color", 0, "ase_146", -1),
        SemanticEdge("alpha", 0, "ase_146", -2),
        SemanticEdge("ase_146", 0, "ase_147", -1),
        SemanticEdge("ase_147", 0, "SurfaceDescription.BaseColor", 0),
        SemanticEdge("alpha", 0, "SurfaceDescription.Alpha", 0),
    ]
    report = {"diagnostics": [], "mappings": []}

    normalize_surface_outputs(
        [custom, passthrough],
        edges,
        {"surface": "Transparent", "blend": "Multiply"},
        {},
        report,
        'Pass {\nName "Forward"\nBlend DstColor Zero, Zero One\nHLSLPROGRAM\nENDHLSL\n}',
    )

    assert report["diagnostics"][0]["code"] == "ALPHA_MODULATE_UNPROVEN"
    assert report["surface_semantics"]["unresolved"]["source_node"] == "146"


def _native_lerp_case(*, white=(1.0, 1.0, 1.0), alpha_source="alpha", reroute=False):
    white_node = SemanticNode("30", "white", "vector3", [0.0, 0.0],
                              {0: "X", 1: "Y", 2: "Z"}, {0: "Out"},
                              {0: white[0], 1: white[1], 2: white[2]})
    color_node = SemanticNode("31", "color", "vector3", [0.0, 100.0],
                              {0: "X", 1: "Y", 2: "Z"}, {0: "Out"},
                              {0: .2, 1: .3, 2: .4})
    alpha_node = SemanticNode("32", "alpha", "float", [0.0, 200.0],
                              {0: "Value"}, {0: "Out"}, {0: .5})
    other_alpha = SemanticNode("33", "other_alpha", "float", [0.0, 300.0],
                               {0: "Value"}, {0: "Out"}, {0: .25})
    lerp = SemanticNode("34", "modulate", "lerp", [200.0, 100.0],
                        {0: "A", 1: "B", 2: "T"}, {0: "Out"})
    nodes = [white_node, color_node, alpha_node, other_alpha, lerp]
    output = "modulate"
    edges = [
        SemanticEdge("white", 0, "modulate", -1),
        SemanticEdge("color", 0, "modulate", -2),
        SemanticEdge(alpha_source, 0, "modulate", -3),
        SemanticEdge("alpha", 0, "SurfaceDescription.Alpha", 0),
    ]
    if reroute:
        route = SemanticNode("35", "route", "reroute", [400.0, 100.0],
                             {0: "In"}, {0: "Out"})
        nodes.append(route)
        edges.append(SemanticEdge("modulate", 0, "route", -1))
        output = "route"
    edges.append(SemanticEdge(output, 0, "SurfaceDescription.BaseColor", 0))
    mappings = {node.source_id: {0: (node.target_id, 0)} for node in nodes}
    report = {"diagnostics": [], "mappings": [
        {"source_nodes": [node.source_id], "target_nodes": [node.target_id], "kind": "direct"}
        for node in nodes
    ]}
    return nodes, edges, mappings, report


@pytest.mark.parametrize("reroute", [False, True])
def test_native_lerp_alpha_modulate_is_folded(reroute):
    nodes, edges, mappings, report = _native_lerp_case(reroute=reroute)

    result_nodes, result_edges = normalize_surface_outputs(
        nodes,
        edges,
        {"surface": "Transparent", "blend": "Multiply"},
        mappings,
        report,
        'Pass {\nName "Forward"\nBlend DstColor Zero, Zero One\nHLSLPROGRAM\nENDHLSL\n}',
    )

    assert SemanticEdge("color", 0, "SurfaceDescription.BaseColor", 0) in result_edges
    assert SemanticEdge("alpha", 0, "SurfaceDescription.Alpha", 0) in result_edges
    assert not any(node.target_id in {"white", "modulate", "route"} for node in result_nodes)
    rewrite = report["surface_semantics"]["rewrites"][0]
    assert rewrite["kind"] == "fold_native_lerp_alpha_modulate_into_multiply_target"
    assert rewrite["matcher_version"] == 4
    assert report["diagnostics"] == []


@pytest.mark.parametrize(
    ("white", "alpha_source"),
    [((.5, 1.0, 1.0), "alpha"), ((1.0, 1.0, 1.0), "other_alpha")],
)
def test_other_native_lerp_is_not_folded(white, alpha_source):
    nodes, edges, mappings, report = _native_lerp_case(
        white=white, alpha_source=alpha_source
    )

    result_nodes, result_edges = normalize_surface_outputs(
        nodes,
        edges,
        {"surface": "Transparent", "blend": "Multiply"},
        mappings,
        report,
        'Pass {\nName "Forward"\nBlend DstColor Zero, Zero One\nHLSLPROGRAM\nENDHLSL\n}',
    )

    assert result_nodes == nodes
    assert result_edges == edges
    assert report["surface_semantics"]["rewrites"] == []


def test_shared_alpha_modulate_is_kept_but_base_color_is_bypassed():
    extra = [SemanticEdge("ase_146", 0, "consumer", -1)]
    (nodes, edges), mappings, report = _normalize(extra_edges=extra)

    assert [node.target_id for node in nodes] == ["ase_146"]
    assert "146" in mappings
    assert SemanticEdge("color", 0, "SurfaceDescription.BaseColor", 0) in edges
    assert extra[0] in edges
    assert report["surface_semantics"]["rewrites"][0]["removed"] is False


def test_independent_source_alpha_blend_is_recorded_as_unrepresentable():
    shader = '''
        Name "Forward"
        Blend DstColor Zero, One Zero
        HLSLPROGRAM
    '''
    (_, _), _, report = _normalize(source_text=shader)

    semantics = report["surface_semantics"]
    assert semantics["rgb_blend_equivalent"] is True
    assert semantics["alpha_blend_equivalent"] is False
    assert semantics["source_pass_blend"]["alpha"] == ["One", "Zero"]
    assert semantics["target_pass_blend"]["alpha"] == ["Zero", "One"]
    assert report["diagnostics"][0]["code"] == "ALPHA_BLEND_UNREPRESENTABLE"


def test_matching_multiply_pass_blend_is_fully_equivalent():
    shader = '''
        Name "Forward"
        Blend DstColor Zero, Zero One
        HLSLPROGRAM
    '''
    (_, _), _, report = _normalize(source_text=shader)

    semantics = report["surface_semantics"]
    assert semantics["rgb_blend_equivalent"] is True
    assert semantics["alpha_blend_equivalent"] is True
    assert report["diagnostics"] == []
