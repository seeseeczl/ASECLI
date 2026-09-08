"""REG-0026: EditorGraphSpec v3 algorithm-graph parsing and expansion."""

from __future__ import annotations

import pytest

from asecli.bridge.editor_spec import EditorGraphSpec, SpecError


TEMPLATE_GUID = "2992e84f91cbeb14eab234972e07ea9d"



def sphere_mask_recipe() -> dict:
    return {
        "alias": "sphere_1",
        "kind": "recipe",
        "position": [280, 20],
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
    }


def v3_spec(nodes, connections=None) -> dict:
    return {
        "version": 3,
        "primitives_version": 1,
        "template": {"guid": TEMPLATE_GUID, "shader_name": "SGCLI/Example/Unlit"},
        "nodes": nodes,
        "connections": connections or [],
    }


def test_v3_sphere_mask_recipe_parses_and_expands_natively():
    raw = v3_spec([
        {"alias": "wp", "kind": "primitive", "position": [-280, 20], "op": "world_position"},
        sphere_mask_recipe(),
    ], connections=[
        {"from": {"node": "wp", "port": 0}, "to": {"node": "sphere_1", "port": 0}},
    ])

    spec = EditorGraphSpec.from_dict(raw)

    recipe = spec.nodes[1]
    assert recipe.kind == "recipe"
    assert recipe.recipe == "sphere_mask"
    assert recipe.expansion_is_native() is True
    manifest = recipe.manifest_entry()
    assert manifest["type"] == "Recipe"
    assert manifest["expansion_nodes"] == [
        {"id": "d", "type": "DistanceOpNode"},
        {"id": "s", "type": "SimpleSubtractOpNode"},
        {"id": "h", "type": "OneMinusNode"},
        {"id": "dv", "type": "SimpleDivideOpNode"},
        {"id": "sat", "type": "SaturateNode"},
        {"id": "out", "type": "OneMinusNode"},
    ]


def test_v3_const_primitive_dispatches_shape():
    from asecli.bridge._editor_primitives import const_class, const_output_type

    assert const_class("43758.5453") == "RangedFloatNode"
    assert const_class("float2(12.9898, 78.233)") == "Vector2Node"
    assert const_class("float3(1, 2, 3)") == "Vector3Node"
    assert const_class("float4(1, 2, 3, 4)") == "Vector4Node"
    assert const_output_type("float2(1, 2)") == "FLOAT2"


def test_v3_unknown_op_recipe_falls_back_to_custom_expression():
    raw = v3_spec([
        {
            "alias": "unknown_1",
            "kind": "recipe",
            "position": [0, 0],
            "recipe": "noise_thing",
            "code": "return float4(0,0,0,0);",
            "output_type": "FLOAT4",
            "inputs": [{"name": "In", "type": "FLOAT4"}],
            "expansion": {
                "primitives": [{"id": "x", "op": "voronoi_3d", "args": ["In"]}],
                "output": "x",
            },
        }
    ])

    spec = EditorGraphSpec.from_dict(raw)
    recipe = spec.nodes[0]
    assert recipe.expansion_is_native() is False
    manifest = recipe.manifest_entry()
    assert manifest["type"] == "CustomExpressionNode"
    assert manifest["name"] == "noise_thing"


def test_v3_top_level_primitive_rejects_unknown_op():
    raw = v3_spec([
        {"alias": "p", "kind": "primitive", "position": [0, 0], "op": "voronoi_3d"},
    ])
    with pytest.raises(SpecError, match="closure"):
        EditorGraphSpec.from_dict(raw)


def test_v3_requires_primitives_version_and_rejects_unsupported():
    raw = v3_spec([])
    raw.pop("primitives_version")
    with pytest.raises(SpecError, match="primitives_version"):
        EditorGraphSpec.from_dict(raw)

    raw = v3_spec([])
    raw["primitives_version"] = 99
    with pytest.raises(SpecError, match="not supported"):
        EditorGraphSpec.from_dict(raw)


def test_v3_recipe_rejects_forward_reference_and_cycle():
    # arg references a primitive declared later (forward reference).
    raw = v3_spec([{
        "alias": "r", "kind": "recipe", "position": [0, 0], "recipe": "bad",
        "code": "return 0;", "output_type": "FLOAT",
        "inputs": [{"name": "A", "type": "FLOAT"}],
        "expansion": {
            "primitives": [
                {"id": "a", "op": "add", "args": ["A", "b"]},
                {"id": "b", "op": "mul", "args": ["A", "A"]},
            ],
            "output": "a",
        },
    }])
    with pytest.raises(SpecError, match="undeclared"):
        EditorGraphSpec.from_dict(raw)

    # output references an input name (not a primitive) -> still valid, but
    # a self-referential id is not (b is declared after a's arg already failed).
    raw = v3_spec([{
        "alias": "r", "kind": "recipe", "position": [0, 0], "recipe": "ok",
        "code": "return 0;", "output_type": "FLOAT",
        "inputs": [{"name": "A", "type": "FLOAT"}],
        "expansion": {
            "primitives": [{"id": "a", "op": "negate", "args": ["A"]}],
            "output": "a",
        },
    }])
    spec = EditorGraphSpec.from_dict(raw)
    assert spec.nodes[0].expansion.output == "a"


def test_v3_property_semantic_fields_roundtrip():
    raw = v3_spec([
        {
            "alias": "radius", "kind": "property", "position": [-560, 20],
            "type": "RangedFloatNode", "property_name": "_Radius",
            "inspector_name": "球罩半径", "parameter_type": "Property",
            "tooltip": "控制球罩边缘半径。",
            "precision": "Float", "default": 0.5, "min": 0.0, "max": 2.0,
        }
    ])

    spec = EditorGraphSpec.from_dict(raw)
    node = spec.nodes[0]
    assert node.precision == "Float"
    assert node.default == 0.5
    assert node.min == 0.0
    assert node.max == 2.0
    manifest = node.manifest_entry()
    assert manifest["precision"] == "Float"
    assert manifest["default"] == 0.5
    assert manifest["min"] == 0.0
    assert manifest["max"] == 2.0


def test_v3_property_semantic_validation():
    raw = v3_spec([
        {"alias": "r", "kind": "property", "position": [0, 0], "type": "RangedFloatNode",
         "property_name": "_R", "inspector_name": "半径", "parameter_type": "Property",
         "tooltip": "半径。", "min": 2.0, "max": 1.0},
    ])
    with pytest.raises(SpecError, match="min"):
        EditorGraphSpec.from_dict(raw)

    raw = v3_spec([
        {"alias": "r", "kind": "property", "position": [0, 0], "type": "RangedFloatNode",
         "property_name": "_R", "inspector_name": "半径", "parameter_type": "Property",
         "tooltip": "半径。", "precision": "Quadruple"},
    ])
    with pytest.raises(SpecError, match="precision"):
        EditorGraphSpec.from_dict(raw)
