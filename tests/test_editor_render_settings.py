"""复杂 SG 接入契约的边界与 manifest。"""

import copy
import pytest
from asecli.bridge.editor_spec import EditorGraphSpec, SpecError


def example():
    return {
        "version": 3,
        "primitives_version": 1,
        "template": {
            "guid": "2992e84f91cbeb14eab234972e07ea9d",
            "shader_name": "Tests/Wave",
            "settings": {
                "surface": "Transparent",
                "blend": "Multiply",
                "two_sided": "On",
                "vertex_position": "Absolute",
                "cast_shadows": False,
            },
        },
        "nodes": [
            {
                "alias": "clock",
                "kind": "custom_expression",
                "position": [0, 0],
                "name": "Time",
                "code": "_Time.y",
                "output_type": "FLOAT",
                "inputs": [],
            }
        ],
        "connections": [
            {"from": {"node": "clock", "port": 0}, "to": {"node": "master", "port": 3}}
        ],
    }


def test_settings_zero_input_roundtrip_manifest():
    raw = example()
    s = EditorGraphSpec.from_dict(raw)
    assert s.to_dict() == raw
    assert s.expected_manifest()["template"] == raw["template"]


@pytest.mark.parametrize(
    "settings",
    [{"surface": "Solid"}, {"cast_shadows": 1}, {"unknown": False}, {"surface": None}],
)
def test_settings_reject_unrecognized_or_wrong_types(settings):
    raw = example()
    raw["template"]["settings"] = settings
    with pytest.raises(SpecError):
        EditorGraphSpec.from_dict(raw)


def test_texture_binding_and_hdr_manifest():
    raw = example()
    raw["nodes"] += [
        {
            "alias": "color",
            "kind": "property",
            "type": "ColorNode",
            "position": [0, 0],
            "property_name": "_Tint",
            "inspector_name": "颜色",
            "tooltip": "测试颜色",
            "parameter_type": "Property",
            "default": [0.1, 0.2, 0.3, 1],
            "hdr": True,
        },
        {
            "alias": "texture",
            "kind": "sampler",
            "position": [0, 0],
            "property_name": "_Bound",
            "inspector_name": "纹理",
            "tooltip": "固定纹理",
            "parameter_type": "Property",
            "hidden": True,
            "texture_guid": "a" * 32,
        },
    ]
    s = EditorGraphSpec.from_dict(raw)
    assert s.to_dict() == raw
    assert s.expected_manifest()["nodes"][1]["hdr"] is True
    assert s.expected_manifest()["nodes"][2]["texture_guid"] == "a" * 32
    raw["nodes"][2]["texture_guid"] = "../asset"
    with pytest.raises(SpecError):
        EditorGraphSpec.from_dict(raw)


def test_large_v3_remains_bounded():
    raw = example()
    raw["connections"] = []
    raw["nodes"] = [{**raw["nodes"][0], "alias": f"n{i}"} for i in range(129)]
    assert len(EditorGraphSpec.from_dict(raw).nodes) == 129
    raw["nodes"] = [{**raw["nodes"][0], "alias": f"n{i}"} for i in range(513)]
    with pytest.raises(SpecError, match="512"):
        EditorGraphSpec.from_dict(raw)


def test_large_spec_transport_is_lossless_and_bounded():
    import base64
    import gzip
    import json
    from asecli.bridge.editor_create import build_executor_code
    payload = example()
    payload["nodes"] = [{**payload["nodes"][0], "alias":f"node{i}"} for i in range(200)]
    code = build_executor_code(payload)
    assert len(code) <= 50000
    assert "GZipStream" in code
    encoded = code.split('FromBase64String("', 1)[1].split('")', 1)[0]
    assert json.loads(gzip.decompress(base64.b64decode(encoded))) == payload


def test_manifest_rounding_only_applies_to_property_numbers():
    from asecli.bridge.editor_create import manifests_match
    assert manifests_match({"default":[0.735849]}, {"default":[0.7358490228652954]})
    assert not manifests_match({"default":[0.7358]}, {"default":[0.7358490228652954]})
    assert not manifests_match({"port":1.0}, {"port":1})
    assert not manifests_match({"hdr":1}, {"hdr":True})
    assert not manifests_match({"code":"A+B"}, {"code":"A-B"})
