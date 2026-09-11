"""Consumer-owned EditorGraphSpec contract is packaged and strict."""

from __future__ import annotations

import json
import pytest
from jsonschema import Draft202012Validator

from asecli.bridge.editor_spec import SpecError, load_editor_graph_spec
from asecli.contracts import (
    SGCLI_NATIVE_CONSUMER,
    load_editor_graph_schema,
    load_sgcli_native_schema_snapshot,
    validate_editor_graph_spec,
    validate_sgcli_native_spec,
)
from asecli.cli.contract_command import cmd_contract
from asecli.schema_validation import (
    SchemaValidationError,
    unsupported_schema_keywords,
    validate_schema,
)
from types import SimpleNamespace


def test_editor_graph_v3_schema_is_authoritative_and_strict():
    schema = load_editor_graph_schema(3)
    assert schema["properties"]["version"] == {"const": 3}
    assert schema["properties"]["primitives_version"] == {"const": 1}
    assert schema["additionalProperties"] is False
    assert schema["$defs"]["generic_node"]["additionalProperties"] is False


def test_unknown_editor_graph_contract_version_fails():
    with pytest.raises(ValueError, match="unsupported EditorGraphSpec"):
        load_editor_graph_schema(2)


def test_contract_command_returns_authoritative_v3_schema():
    result = cmd_contract(SimpleNamespace(version=3))
    assert result["contract"] == "EditorGraphSpec.v3"
    assert result["schema"]["properties"]["version"] == {"const": 3}


def test_sgcli_consumer_schema_snapshot_is_pinned_and_packaged():
    schema = load_sgcli_native_schema_snapshot()
    assert SGCLI_NATIVE_CONSUMER == {
        "package": "sgcli",
        "version": "0.2.0",
        "contract": "sgcli.native.v3",
        "sha256": "b0cee4774e6a3e4a7dfd32ba1c55f8969ee9c7f5f9d48eb4be7649287e817651",
    }
    assert schema["properties"]["schema"] == {"const": "sgcli.native.v3"}


def test_v3_loader_rejects_unknown_nested_field_before_editor(tmp_path):
    value = {
        "version": 3,
        "primitives_version": 1,
        "template": {
            "guid": "2992e84f91cbeb14eab234972e07ea9d",
            "shader_name": "Tests/Strict",
        },
        "nodes": [
            {
                "alias": "value",
                "kind": "primitive",
                "position": [0, 0],
                "op": "const",
                "value": "1.0",
                "bogus": True,
            }
        ],
        "connections": [],
    }
    path = tmp_path / "Graph.sgcli-to-asecli.spec.json"
    path.write_text(json.dumps(value), encoding="utf-8")
    with pytest.raises(SpecError, match="schema validation failed"):
        load_editor_graph_spec(path)


def test_packaged_contracts_only_use_implemented_schema_keywords():
    assert unsupported_schema_keywords(load_editor_graph_schema()) == []
    assert unsupported_schema_keywords(load_sgcli_native_schema_snapshot()) == []


def test_editor_graph_max_length_is_enforced():
    value = {
        "version": 3,
        "primitives_version": 1,
        "template": {
            "guid": "2992e84f91cbeb14eab234972e07ea9d",
            "shader_name": "x" * 256,
        },
        "nodes": [],
        "connections": [],
    }
    with pytest.raises(SchemaValidationError, match="maxLength"):
        validate_editor_graph_spec(value)


def test_native_property_names_and_contains_are_enforced():
    empty_input_name = {
        "schema": "sgcli.native.v3",
        "name": "Contract/Test",
        "nodes": [{"id": "n", "type": "add", "inputs": {"": 1.0}}],
        "connections": [],
    }
    with pytest.raises(SchemaValidationError, match="minLength"):
        validate_sgcli_native_spec(empty_input_name)

    function_without_output = {
        "schema": "sgcli.native.v3",
        "name": "Contract/Test",
        "nodes": [{
            "id": "f",
            "type": "custom-function",
            "function": {
                "name": "OnlyInput",
                "source": "String",
                "body": "void OnlyInput(float X) {}",
                "ports": [{"name": "X", "type": "Vector1", "direction": "Input"}],
            },
        }],
        "connections": [],
    }
    with pytest.raises(SchemaValidationError, match="required item"):
        validate_sgcli_native_spec(function_without_output)


@pytest.mark.parametrize("value,schema", [
    ("x" * 256, {"type": "string", "maxLength": 255}),
    ([{"direction": "Input"}], {
        "type": "array",
        "contains": {"properties": {"direction": {"const": "Output"}}, "required": ["direction"]},
    }),
    ({"": 1}, {"type": "object", "propertyNames": {"minLength": 1}}),
])
def test_builtin_validator_matches_draft_202012_for_contract_keywords(value, schema):
    expected_valid = Draft202012Validator(schema).is_valid(value)
    try:
        validate_schema(value, schema)
    except SchemaValidationError:
        actual_valid = False
    else:
        actual_valid = True
    assert actual_valid is expected_valid
