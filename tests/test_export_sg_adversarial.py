"""Adversarial regression tests for ASE -> SG export fail-closed gates."""

from __future__ import annotations

import json
import os
from pathlib import Path
from types import SimpleNamespace

import pytest

from asecli.cli.commands import CliError
from asecli.cli.export_sg_command import cmd_export_sg
from asecli.export_sg import ExportError, build_candidate
from tests.test_export_sg import _configured_math, _master, _node, _shader, unity_project


def test_dangling_wire_is_rejected_before_mapping(unity_project: Path):
    value = _node("AmplifyShaderEditor.RangedFloatNode", 10, "-400,0")
    source = unity_project / "dangling.shader"
    source.write_text(_shader(value, _master(), wires=[
        "WireConnection;1;2;10;0", "WireConnection;999;0;10;0",
    ]), encoding="utf-8")

    with pytest.raises(ExportError) as raised:
        build_candidate(source, unity_project)
    report = raised.value.report
    assert "DANGLING_WIRE" in {row["code"] for row in report["diagnostics"]}
    assert report["source_validation"]["error_count"] == 1
    assert report["verification"]["source_structure"]["status"] == "failed"


@pytest.mark.parametrize(("label", "value", "target_option"), [
    ("Cast Shadows", "0", ("castShadows", False)),
    ("Receive Shadows", "0", ("receiveShadows", False)),
    ("LOD CrossFade", "1", ("supportsLodCrossFade", True)),
])
def test_master_effect_options_are_mapped(unity_project: Path, label, value, target_option):
    node = _node("AmplifyShaderEditor.RangedFloatNode", 10, "-400,0")
    master = _master()
    master[master.index(label) + 1] = value
    source = unity_project / f"master-{target_option[0]}.shader"
    source.write_text(_shader(node, master, wires=["WireConnection;1;2;10;0"]), encoding="utf-8")

    candidate, _, _, _ = build_candidate(source, unity_project)
    assert candidate["target"]["options"][target_option[0]] is target_option[1]


def test_unmapped_master_option_fails_closed(unity_project: Path):
    node = _node("AmplifyShaderEditor.RangedFloatNode", 10, "-400,0")
    master = _master()
    master[master.index("Built-in Fog") + 1] = "0"
    source = unity_project / "fog-off.shader"
    source.write_text(_shader(node, master, wires=["WireConnection;1;2;10;0"]), encoding="utf-8")

    with pytest.raises(ExportError) as raised:
        build_candidate(source, unity_project)
    assert "TARGET_OPTION_UNSUPPORTED" in {row["code"] for row in raised.value.report["diagnostics"]}


def test_uncertified_depth_setting_fails_closed(unity_project: Path):
    node = _node("AmplifyShaderEditor.RangedFloatNode", 10, "-400,0")
    master = _master() + ["Write Depth", "1", "0"]
    source = unity_project / "depth-write.shader"
    source.write_text(_shader(node, master, wires=["WireConnection;1;2;10;0"]), encoding="utf-8")

    with pytest.raises(ExportError) as raised:
        build_candidate(source, unity_project)
    item = next(row for row in raised.value.report["diagnostics"]
                if row["code"] == "TARGET_OPTION_UNSUPPORTED")
    assert item["reason"]["option"] == "Write Depth"


@pytest.mark.parametrize("attributes", ["", "[HideInInspector] "])
def test_external_shaderlab_property_fails_closed(unity_project: Path, attributes: str):
    node = _node("AmplifyShaderEditor.RangedFloatNode", 10, "-400,0")
    source = unity_project / "external-property.shader"
    source.write_text(_shader(node, _master(), wires=["WireConnection;1;2;10;0"],
        properties=f'    {attributes}_ExternalGain("External", Float) = 2.0'), encoding="utf-8")

    with pytest.raises(ExportError) as raised:
        build_candidate(source, unity_project)
    diagnostic = next(row for row in raised.value.report["diagnostics"]
                      if row["code"] == "SHADERLAB_PROPERTY_UNMAPPED")
    assert diagnostic["reason"]["property"] == "_ExternalGain"


def test_unsupported_node_blocks_without_partial_spec(unity_project: Path):
    unknown = ["Node", "AmplifyShaderEditor.CustomExpressionNode", "99", "-400,0", "Inherit", "False"]
    source = unity_project / "unsupported.shader"
    source.write_text(_shader(unknown, _master(), wires=["WireConnection;1;2;99;0"]), encoding="utf-8")
    with pytest.raises(ExportError) as raised:
        build_candidate(source, unity_project)
    assert raised.value.report["diagnostics"][0]["source_node_id"] == "99"
    assert raised.value.report["verification"]["semantic_mapping"]["status"] == "blocked"


def test_write_failure_emits_only_report(monkeypatch, unity_project: Path):
    unknown = ["Node", "AmplifyShaderEditor.CustomExpressionNode", "99", "-400,0", "Inherit", "False"]
    source = unity_project / "unsupported.shader"
    source.write_text(_shader(unknown, _master(), wires=["WireConnection;1;2;99;0"]), encoding="utf-8")
    args = SimpleNamespace(file=str(source), target_project=str(unity_project), out_dir=str(unity_project),
        name=None, asset_map=None, sgcli_bin="sgcli", sg_schema=None, mcp_url="http://127.0.0.1:9080/mcp",
        ase_mcp_url=None, write=True)
    with pytest.raises(CliError) as raised:
        cmd_export_sg(args)
    assert raised.value.code == "SG_EXPORT_BLOCKED"
    assert not (unity_project / "graph.sg.json").exists()
    report = json.loads((unity_project / "report.json").read_text(encoding="utf-8"))
    assert report["diagnostics"][0]["source_node_id"] == "99"


def test_malformed_source_write_emits_a_failure_report(unity_project: Path):
    source = unity_project / "malformed.shader"
    source.write_text("Shader \"Broken\" {}", encoding="utf-8")
    args = SimpleNamespace(file=str(source), target_project=str(unity_project), out_dir=str(unity_project),
        name=None, asset_map=None, sgcli_bin="sgcli", sg_schema=None, mcp_url="http://127.0.0.1:9080/mcp",
        ase_mcp_url=None, write=True)
    with pytest.raises(CliError) as raised:
        cmd_export_sg(args)
    assert raised.value.code == "SG_EXPORT_BLOCKED"
    assert not (unity_project / "graph.sg.json").exists()
    report = json.loads((unity_project / "report.json").read_text(encoding="utf-8"))
    assert report["verification"]["source_parse"]["status"] == "failed"


def test_successful_write_is_bare_spec_and_never_overwrites(monkeypatch, unity_project: Path):
    value = _node("AmplifyShaderEditor.RangedFloatNode", 10, "-400,0", precision="Float")
    value[19] = "0.375"
    source = unity_project / "scalar.shader"
    source.write_text(_shader(value, _master(), wires=["WireConnection;1;2;10;0"]), encoding="utf-8")

    class FakeAdapter:
        def __init__(self, binary, mcp_url): pass
        def doctor(self):
            return {"project": str(unity_project), "supported": True, "urp_available": True, "unity": "2022.3", "shadergraph": "14.1"}
        def catalog(self): return {"nodes": []}
        def configured(self, spec):
            data = _configured_math()
            data["configured_graph"]["nodes"] = [data["configured_graph"]["nodes"][0], data["configured_graph"]["nodes"][2]]
            return data
        def precheck(self, spec, inventory, outputs=None):
            return {"validator": "sgcli.native.spec_v2.prepare", "accepted": True}
        def preview(self, target, spec): return {"preview": True, "written": False}

    monkeypatch.setattr("asecli.cli.export_sg_command.SgcliAdapter", FakeAdapter)
    args = SimpleNamespace(file=str(source), target_project=str(unity_project), out_dir=str(unity_project),
        name=None, asset_map=None, sgcli_bin="sgcli", sg_schema=None, mcp_url="http://127.0.0.1:9080/mcp",
        ase_mcp_url=None, write=True)
    result = cmd_export_sg(args)
    graph = json.loads((unity_project / "graph.sg.json").read_text(encoding="utf-8"))
    report = json.loads((unity_project / "report.json").read_text(encoding="utf-8"))
    assert graph["schema"] == "sgcli.native.v2" and "ok" not in graph and "data" not in graph
    from asecli.export_sg import validate_schema
    validate_schema(graph, None)
    assert report["schema"] == "asecli.sg-conversion-report.v1" and result["written"] is True
    assert result["graph_json"] == str(unity_project / "graph.sg.json")
    assert result["report_json"] == str(unity_project / "report.json")
    assert result["write"]["committed"] is True
    with pytest.raises(CliError, match="never overwrites"):
        cmd_export_sg(args)


def test_write_new_does_not_overwrite_racing_writer(monkeypatch, tmp_path: Path):
    from asecli.cli.export_sg_command import _write_new

    target = tmp_path / "graph.sg.json"
    real_link = os.link

    def racing_link(source, destination):
        Path(destination).write_text("other writer", encoding="utf-8")
        return real_link(source, destination)

    monkeypatch.setattr("asecli.cli.export_sg_command.os.link", racing_link)
    with pytest.raises(CliError) as raised:
        _write_new(target, {"ours": True})
    assert raised.value.code == "WRITE_CONFLICT"
    assert target.read_text(encoding="utf-8") == "other writer"


def test_write_new_rejects_symlink_without_touching_target(tmp_path: Path):
    from asecli.cli.export_sg_command import _write_new

    victim = tmp_path / "victim.json"
    victim.write_text("sentinel", encoding="utf-8")
    target = tmp_path / "graph.sg.json"
    target.symlink_to(victim)
    with pytest.raises(CliError) as raised:
        _write_new(target, {"ours": True})
    assert raised.value.code == "WRITE_CONFLICT"
    assert victim.read_text(encoding="utf-8") == "sentinel"
    assert target.is_symlink()


def test_write_new_cleanup_failure_is_a_committed_warning(monkeypatch, tmp_path: Path):
    from asecli.cli.export_sg_command import _write_new

    target = tmp_path / "graph.sg.json"
    original_unlink = Path.unlink

    def fail_temp_cleanup(path, *args, **kwargs):
        if path.name.endswith(".tmp"):
            raise OSError("cleanup unavailable")
        return original_unlink(path, *args, **kwargs)

    monkeypatch.setattr(Path, "unlink", fail_temp_cleanup)
    result = _write_new(target, {"ours": True})
    assert result["committed"] is True
    assert result["warnings"] == ["temporary link cleanup failed: cleanup unavailable"]
    assert result["temporary_path"].endswith(".tmp")
    assert json.loads(target.read_text(encoding="utf-8")) == {"ours": True}


def test_write_pair_second_file_race_reports_partial_commit(monkeypatch, tmp_path: Path):
    from asecli.cli.export_sg_command import _write_pair

    graph = tmp_path / "graph.sg.json"
    report = tmp_path / "report.json"
    real_link = os.link
    calls = 0

    def racing_second_link(source, destination):
        nonlocal calls
        calls += 1
        if calls == 2:
            Path(destination).write_text("other writer", encoding="utf-8")
        return real_link(source, destination)

    monkeypatch.setattr("asecli.cli.export_sg_command.os.link", racing_second_link)
    with pytest.raises(CliError) as raised:
        _write_pair(graph, {"graph": True}, {"report": True})
    assert raised.value.code == "WRITE_PARTIAL"
    assert raised.value.data["committed_files"][0]["path"] == str(graph)
    assert json.loads(graph.read_text(encoding="utf-8")) == {"graph": True}
    assert report.read_text(encoding="utf-8") == "other writer"


def test_repeated_export_has_deterministic_graph_and_report(monkeypatch, unity_project: Path):
    value = _node("AmplifyShaderEditor.RangedFloatNode", 10, "-400,0")
    source = unity_project / "stable.shader"
    source.write_text(_shader(value, _master(), wires=["WireConnection;1;2;10;0"]), encoding="utf-8")

    class FakeAdapter:
        counter = 0
        def __init__(self, binary, mcp_url): pass
        def doctor(self):
            return {"project": str(unity_project), "supported": True, "urp_available": True}
        def catalog(self): return {"nodes": []}
        def configured(self, spec):
            data = _configured_math()
            data["configured_graph"]["nodes"] = [data["configured_graph"]["nodes"][0], data["configured_graph"]["nodes"][2]]
            return data
        def precheck(self, spec, inventory, outputs=None): return {"accepted": True}
        def preview(self, target, spec):
            self.__class__.counter += 1
            suffix = self.__class__.counter
            return {"preview": True, "written": False,
                    "nodes": [{"id": f"random-{suffix}"}],
                    "connections": [], "candidate_sha256": f"random-{suffix}"}

    monkeypatch.setattr("asecli.cli.export_sg_command.SgcliAdapter", FakeAdapter)
    payloads = []
    for name in ("first", "second"):
        directory = unity_project / name
        directory.mkdir()
        args = SimpleNamespace(file=str(source), target_project=str(unity_project), out_dir=str(directory),
            name=None, asset_map=None, sgcli_bin="sgcli", sg_schema=None,
            mcp_url="http://127.0.0.1:9080/mcp", ase_mcp_url=None, write=True)
        cmd_export_sg(args)
        payloads.append(((directory / "graph.sg.json").read_bytes(), (directory / "report.json").read_bytes()))
    assert payloads[0] == payloads[1]


def _write_texture_asset(project: Path, relative: str, guid: str, *, srgb: int = 1,
                         texture_type: int = 0, filter_mode: int = 1,
                         wrap_u: int = 0, compression: int = 1) -> None:
    asset = project / relative
    asset.parent.mkdir(parents=True, exist_ok=True)
    asset.write_bytes(b"texture")
    asset.with_name(asset.name + ".meta").write_text(f"""fileFormatVersion: 2
guid: {guid}
TextureImporter:
  mipmaps:
    enableMipMap: 1
    sRGBTexture: {srgb}
  textureSettings:
    filterMode: {filter_mode}
    aniso: 1
    wrapU: {wrap_u}
    wrapV: 0
    wrapW: 0
  alphaUsage: 1
  alphaIsTransparency: 0
  textureType: {texture_type}
  textureShape: 1
  platformSettings:
  - buildTarget: DefaultTexturePlatform
    textureCompression: {compression}
    compressionQuality: 50
    crunchedCompression: 0
""", encoding="utf-8")


def test_texture_importer_evidence_is_recorded(unity_project: Path):
    guid = "0123456789abcdef0123456789abcdef"
    _write_texture_asset(unity_project, "Assets/Textures/Main.png", guid)
    sampler = _node("AmplifyShaderEditor.SamplerNode", 10, "-400,0")
    sampler[6:9] = ["Property", "_MainTex", "主贴图"]
    sampler[20] = guid
    source = unity_project / "texture-importer.shader"
    source.write_text(_shader(sampler, _master(), wires=["WireConnection;1;2;10;0"],
        properties='    _MainTex("主贴图", 2D) = "white" {}'), encoding="utf-8")

    candidate, report, nodes, _ = build_candidate(source, unity_project)
    assert candidate["properties"][0]["default"] == "Assets/Textures/Main.png"
    assert report["dependencies"][0]["status"] == "verified_importer"
    assert report["dependencies"][0]["importer"]["sRGBTexture"] == 1
    sample = next(row for row in nodes if row.target_type == "sample-texture")
    assert sample.settings["textureType"] == "Default"


@pytest.mark.parametrize("target_settings", [
    {"srgb": 0}, {"texture_type": 1}, {"filter_mode": 0},
    {"wrap_u": 1}, {"compression": 0},
])
def test_texture_importer_mismatch_fails_closed(tmp_path: Path, target_settings):
    source_project = tmp_path / "source"
    target_project = tmp_path / "target"
    for project in (source_project, target_project):
        (project / "Assets").mkdir(parents=True)
        (project / "ProjectSettings").mkdir()
    guid = "fedcba9876543210fedcba9876543210"
    _write_texture_asset(source_project, "Assets/Textures/Main.png", guid, srgb=1)
    _write_texture_asset(target_project, "Assets/Textures/Main.png",
                         "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa", **target_settings)
    asset_map = tmp_path / "assets.json"
    asset_map.write_text(json.dumps({guid: "Assets/Textures/Main.png"}), encoding="utf-8")
    sampler = _node("AmplifyShaderEditor.SamplerNode", 10, "-400,0")
    sampler[6:9] = ["Property", "_MainTex", "主贴图"]
    sampler[20] = guid
    source = source_project / "Assets" / "texture.shader"
    source.write_text(_shader(sampler, _master(), wires=["WireConnection;1;2;10;0"],
        properties='    _MainTex("主贴图", 2D) = "white" {}'), encoding="utf-8")

    with pytest.raises(ExportError) as raised:
        build_candidate(source, target_project, asset_map_path=asset_map)
    assert "TEXTURE_IMPORTER_UNVERIFIED" in {row["code"] for row in raised.value.report["diagnostics"]}
