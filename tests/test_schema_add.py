"""REG-0013: schema-driven node construction is complete and version-safe."""

from __future__ import annotations

import json
from pathlib import Path

from asecli.cli.main import app
from asecli.core import AseFile, node_from_schema
from asecli.schema import allows_mutation, load, schema_for


FIXTURES = Path(__file__).parent / "fixtures"
RUNTIME_TYPE = "AmplifyShaderEditor.SaturateNode"


def test_runtime_node_includes_six_field_fixed_prefix():
    graph = AseFile.from_path(FIXTURES / "HLIT.shader").graph
    schema = schema_for(RUNTIME_TYPE)
    assert schema is not None

    node = node_from_schema(graph, schema, 500, "0,0", RUNTIME_TYPE)

    assert node.raw_fields[4:6] == ["Inherit", "False"]
    assert len(node.raw_fields) == 6 + len(schema["fields"])


def test_ten_mutable_runtime_layouts_build_complete_prefix():
    graph = AseFile.from_path(FIXTURES / "HLIT.shader").graph
    schemas = load()["types"]
    mutable = [
        (name, schema)
        for name, schema in sorted(schemas.items())
        if schema.get("source") == "runtime" and schema.get("layout_ok") is True
    ][:10]
    assert len(mutable) == 10

    for index, (name, schema) in enumerate(mutable, 600):
        node = node_from_schema(graph, schema, index, "0,0", name)
        assert node.raw_fields[4:6] == ["Inherit", "False"], name
        assert len(node.raw_fields) == 6 + len(schema["fields"]), name


def test_runtime_opaque_layout_is_not_mutable():
    opaque_name = next(
        name
        for name, schema in load()["types"].items()
        if schema.get("source") == "runtime" and schema.get("layout_ok") is False
    )
    assert allows_mutation(opaque_name) is False


def test_cross_version_add_node_is_rejected_without_writing(tmp_path, capsys):
    target = tmp_path / "old-version.asset"
    target.write_bytes((FIXTURES / "step-antialiasing.function.txt").read_bytes())
    before = target.read_bytes()

    rc = app(
        [
            "add-node",
            str(target),
            "--type",
            RUNTIME_TYPE,
            "--id",
            "500",
            "--write",
        ]
    )
    payload = json.loads(capsys.readouterr().out)

    assert rc == 2
    assert payload["ok"] is False
    assert payload["error"]["code"] == "SCHEMA_VERSION_MISMATCH"
    assert target.read_bytes() == before
