"""REG-0009: runtime-extracted schemas must match real-file node lines field-for-field."""

from pathlib import Path

from asecli.core import AseFile
from asecli.schema import allows_mutation, is_known, load, schema_for

FIXTURES = Path(__file__).parent / "fixtures"


def _node_lines(path: str) -> list[str]:
    f = AseFile.from_path(FIXTURES / path)
    return [raw for kind, raw in f.graph.instructions if kind == "node"]


def test_all_fixture_node_types_known():
    lines = _node_lines("HLIT.shader") + _node_lines("step-antialiasing.function.txt")
    unknown = []
    for line in lines:
        type_name = line.split(";")[1]
        if not is_known(type_name):
            unknown.append(type_name)
    assert unknown == []


def test_sample_lines_match_runtime_layout():
    """For runtime-extracted types, field count of real lines must equal schema count.

    Strict count only when fixture version matches the extracted ASE version
    (serialization layout may differ across ASE versions).
    """
    runtime_version = next(
        (v["ase_version"] for v in load()["types"].values() if v.get("source") == "runtime"),
        None,
    )
    if runtime_version:
        runtime_version = runtime_version.removeprefix("Version=")
    checked = 0
    for path in ("HLIT.shader", "step-antialiasing.function.txt"):
        f = AseFile.from_path(FIXTURES / path)
        version_matches = f.graph.version == runtime_version
        for line in [raw for kind, raw in f.graph.instructions if kind == "node"]:
            fields = line.split(";")
            type_name = fields[1]
            s = schema_for(type_name)
            assert s is not None, type_name
            if s.get("source") == "observed":
                assert line in s["samples"], type_name
            elif s.get("source") == "runtime" and version_matches:
                assert len(fields) - 6 == len(s["fields"]), f"{type_name}: {len(fields) - 6} vs {len(s['fields'])}"
            checked += 1
    assert checked >= 15  # 10 master nodes + 7 function nodes minimum coverage


def test_schema_db_size():
    types = load()["types"]
    runtime = sum(1 for v in types.values() if v.get("source") == "runtime")
    assert runtime >= 290


def test_master_nodes_observed_only():
    assert not allows_mutation("AmplifyShaderEditor.TemplateMultiPassMasterNode")
    assert is_known("AmplifyShaderEditor.TemplateMultiPassMasterNode")
