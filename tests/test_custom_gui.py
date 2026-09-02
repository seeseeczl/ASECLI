"""REG-0022: ASE 1.9.6.2 CustomEditor and property-metadata operations."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

from asecli.checks import fix_checksum, verify_checksum
from asecli.core import (
    ASECLI_GUI_EDITOR,
    AseFile,
    SUPPORTED_GUI_EDITORS,
    compiled_custom_editor,
    decode_custom_unicode,
    decode_foldout_title,
    encode_custom_unicode,
    encode_foldout_title,
    inspect_custom_gui,
    parse_graph_text,
    read_property_metadata_tail,
    remove_property_metadata_attribute,
    semantic_attribute,
    set_custom_editor,
    set_property_metadata_attribute,
    sync_compiled_property_metadata,
)


ROOT = Path(__file__).parents[1]
SRC = str(ROOT / "src")
HLIT = ROOT / "tests" / "fixtures" / "HLIT.shader"


def sample_shader(editor: str = "UnityEditor.ShaderGraphLitGUI") -> str:
    text = f'''Shader "Tests/ASECLI"
{{
\tProperties {{
\t\t_BaseColor("基础颜色", Color) = (1,1,1,1)
\t}}
\tSubShader {{}}
\tCustomEditor "{editor}"
\tFallback Off
}}
/*ASEBEGIN
Version=19602
Node;AmplifyShaderEditor.TemplateMultiPassMasterNode;0;0,0;Float;False;False;-1;2;{editor};0;1
Node;AmplifyShaderEditor.TemplateMultiPassMasterNode;1;0,0;Float;False;True;-1;2;{editor};0;1
Node;AmplifyShaderEditor.ColorNode;10;100,100;Inherit;False;Property;_BaseColor;基础颜色;0;0;Create;False;0
Node;AmplifyShaderEditor.ColorNode;11;200,100;Inherit;False;Constant;_Other;非属性;0;0;Create;False;0
ASEEND*/
//CHKSM=PLACEHOLDER'''
    return fix_checksum(text)


def multi_property_shader() -> str:
    text = sample_shader(ASECLI_GUI_EDITOR).replace(
        "\tProperties {\n\t\t_BaseColor(\"基础颜色\", Color) = (1,1,1,1)\n\t}",
        "\tProperties {\n"
        "\t\t_BaseColor(\"基础颜色\", Color) = (1,1,1,1)\n"
        "\t\t_Contrast(\"Contrast\", Range(0, 2)) = 1\n"
        "\t\t_Coat_IO(\"Coat IO\", Float) = 0\n"
        "\t}",
    ).replace(";基础颜色;0;0;Create", ";基础颜色;2;0;Create")
    extra = """Node;AmplifyShaderEditor.RangedFloatNode;12;300,100;Inherit;False;Property;_Contrast;Contrast;0;0;Create;False;0
Node;AmplifyShaderEditor.RangedFloatNode;13;500,100;Inherit;False;Property;_Coat_IO;Coat IO;1;0;Create;False;0
"""
    return fix_checksum(text.replace("ASEEND*/", extra + "ASEEND*/"))


def run_cli(*args: str) -> tuple[int, dict]:
    env = dict(os.environ)
    env["PYTHONPATH"] = SRC
    proc = subprocess.run(
        [sys.executable, "-m", "asecli.cli.main", *args],
        capture_output=True,
        text=True,
        env=env,
    )
    lines = proc.stdout.splitlines()
    assert len(lines) == 1, (proc.stdout, proc.stderr)
    return proc.returncode, json.loads(lines[0])


def test_reads_hlit_graph_and_compiled_custom_editor():
    state = inspect_custom_gui(AseFile.from_path(HLIT))
    assert state["graph_version"] == "19109"
    assert state["editor"] == {
        "main_node_id": "1",
        "graph": "UnityEditor.ShaderGraphLitGUI",
        "compiled": "UnityEditor.ShaderGraphLitGUI",
        "consistent": True,
    }


def test_inspection_returns_property_order_index():
    state = inspect_custom_gui(AseFile.from_text(sample_shader(ASECLI_GUI_EDITOR)))
    assert state["properties"][0]["order_index"] == 0


def test_inspection_advertises_the_asecli_material_gui():
    state = inspect_custom_gui(AseFile.from_text(sample_shader(ASECLI_GUI_EDITOR)))
    assert state["editor"]["graph"] == ASECLI_GUI_EDITOR
    assert state["capabilities"]["built_in_editor"] == ASECLI_GUI_EDITOR
    assert set(state["capabilities"]["supported_editors"]) == SUPPORTED_GUI_EDITORS


def test_custom_editor_updates_only_main_master_and_compiled_directive():
    shader = AseFile.from_text(sample_shader())
    secondary_before = shader.graph.node_by_id("0").to_line()
    change = set_custom_editor(shader, ASECLI_GUI_EDITOR)
    assert change["main_node_id"] == "1"
    assert shader.graph.node_by_id("0").to_line() == secondary_before
    assert shader.graph.node_by_id("1").raw_fields[9] == ASECLI_GUI_EDITOR
    assert compiled_custom_editor(shader) == ASECLI_GUI_EDITOR
    assert shader.serialize().count(f'CustomEditor "{ASECLI_GUI_EDITOR}"') == 1
    set_custom_editor(shader, None)
    assert shader.graph.node_by_id("1").raw_fields[9] == ""
    assert compiled_custom_editor(shader) is None


def test_custom_editor_can_be_inserted_when_compiled_directive_is_missing():
    shader = AseFile.from_text(sample_shader().replace('\tCustomEditor "UnityEditor.ShaderGraphLitGUI"\n', ""))
    assert compiled_custom_editor(shader) is None
    set_custom_editor(shader, ASECLI_GUI_EDITOR)
    assert compiled_custom_editor(shader) == ASECLI_GUI_EDITOR
    assert shader.prefix.index(f'CustomEditor "{ASECLI_GUI_EDITOR}"') < shader.prefix.index("Fallback Off")


def test_property_metadata_unicode_codecs_use_the_verified_utf16_format():
    text = "提示 A\n😀"
    encoded = encode_custom_unicode(text)
    assert encoded.startswith("#63D0#793A#0020#0041#000A#D83D#DE00")
    assert decode_custom_unicode(encoded) == text
    assert decode_foldout_title(encode_foldout_title("基础参数 😀")) == "基础参数 😀"


def test_reads_legacy_foldout_tail_without_using_it_for_new_writes():
    # Unmodified node line from ASE 1.9.6.2 Examples/MZGUI_Test.shader.
    body = """Version=19602
Node;AmplifyShaderEditor.IntNode;122;992,-32;Inherit;False;Property;_Int0;整数;0;0;Create;False;0;0;0;True;0;False;0;0;False;0;1;INT;0;1;[FoldoutMzgui(Foldout #6298#53e0#9875 01)]
"""
    graph = parse_graph_text(body)
    node = graph.node_by_id("122")
    tail = read_property_metadata_tail(graph, node)
    assert tail.attributes == ("[FoldoutMzgui(Foldout #6298#53e0#9875 01)]",)
    assert decode_foldout_title("Foldout #6298#53e0#9875 01") == "Foldout 折叠页 01"


def test_writing_a_legacy_semantic_attribute_migrates_only_that_attribute():
    text = sample_shader(ASECLI_GUI_EDITOR).replace(
        ";基础颜色;0;0;Create;False;0\n",
        ";基础颜色;0;1;[TooltipMzgui(#65E7#6807#63D0#793A)]\n",
    )
    shader = AseFile.from_text(fix_checksum(text))
    set_property_metadata_attribute(
        shader.graph,
        "10",
        semantic_attribute("ASECLITooltip", "新提示"),
    )
    attributes = read_property_metadata_tail(shader.graph, shader.graph.node_by_id("10")).attributes
    assert len(attributes) == 1
    assert attributes[0].startswith("[ASECLITooltip(")


def test_property_metadata_tail_roundtrips_on_verified_19602_layout():
    shader = AseFile.from_text(sample_shader(ASECLI_GUI_EDITOR))
    set_property_metadata_attribute(
        shader.graph,
        "10",
        semantic_attribute("ASECLIHelpBox", "跨版本尾部能力探测"),
    )
    tail = read_property_metadata_tail(shader.graph, shader.graph.node_by_id("10"))
    assert len(tail.attributes) == 1
    assert parse_graph_text(shader.graph.serialize()).node_by_id("10").raw_fields == (
        shader.graph.node_by_id("10").raw_fields
    )


def test_unknown_future_version_rejects_custom_editor_and_tail_without_mutation():
    shader = AseFile.from_text(
        sample_shader(ASECLI_GUI_EDITOR).replace("Version=19602", "Version=25000")
    )
    master = shader.graph.node_by_id("1")
    master.raw_fields[9] = "UNRELATED_FIELD_9"
    shader.graph.replace_node(master)
    node = shader.graph.node_by_id("10")
    node.raw_fields[-2:] = ["FUTURE_SEMANTIC_FLAG", "0"]
    shader.graph.replace_node(node)
    before = shader.serialize()
    with pytest.raises(ValueError, match="unsupported ASE graph version"):
        set_custom_editor(shader, ASECLI_GUI_EDITOR)
    assert shader.serialize() == before
    with pytest.raises(ValueError, match="unsupported ASE graph version"):
        set_property_metadata_attribute(
            shader.graph,
            "10",
            semantic_attribute("ASECLIHelpBox", "不得猜写"),
        )
    assert shader.serialize() == before


def test_real_19109_hlit_exposes_only_verified_custom_editor_capability():
    state = inspect_custom_gui(AseFile.from_path(HLIT))
    assert state["version_capabilities"] == {"custom_editor": True, "property_metadata_tail": False}
    assert state["properties"] == []


def test_cli_unknown_future_version_fails_before_backup_or_write(tmp_path):
    path = tmp_path / "future.shader"
    original = sample_shader(ASECLI_GUI_EDITOR).replace("Version=19602", "Version=25000")
    path.write_text(original, encoding="utf-8")
    code, payload = run_cli(
        "custom-gui",
        str(path),
        "--editor",
        ASECLI_GUI_EDITOR,
        "--property",
        "_BaseColor",
        "--help-box",
        "不得猜写",
        "--write",
    )
    assert code == 2
    assert payload["error"]["code"] == "CUSTOM_GUI_ERROR"
    assert "unsupported ASE graph version" in payload["error"]["message"]
    assert path.read_text(encoding="utf-8") == original
    assert not path.with_suffix(".shader.bak").exists()


def test_unknown_property_tail_fails_closed_instead_of_guessing_an_index():
    shader = AseFile.from_text(sample_shader(ASECLI_GUI_EDITOR))
    node = shader.graph.node_by_id("10")
    node.raw_fields[-1] = "unknown-tail-format"
    shader.graph.replace_node(node)
    with pytest.raises(ValueError, match="no valid property metadata serialization tail"):
        set_property_metadata_attribute(
            shader.graph,
            "10",
            semantic_attribute("ASECLIHelpBox", "不得猜写"),
        )


def test_group_tooltip_helpbox_add_replace_remove_and_count():
    shader = AseFile.from_text(sample_shader(ASECLI_GUI_EDITOR))
    graph = shader.graph
    set_property_metadata_attribute(graph, "10", semantic_attribute("ASECLIFoldout", "基础参数"))
    set_property_metadata_attribute(graph, "10", semantic_attribute("ASECLITooltip", "变量名：_BaseColor\n默认值：(1, 1, 1, 1)"))
    set_property_metadata_attribute(graph, "10", semantic_attribute("ASECLIHelpBox", "请按项目规范设置"))
    set_property_metadata_attribute(graph, "10", semantic_attribute("ASECLITooltip", "变量名：_BaseColor\n默认值：(0.5, 0.5, 0.5, 1)"))
    node = graph.node_by_id("10")
    tail = read_property_metadata_tail(graph, node)
    assert node.raw_fields[tail.count_index] == "3"
    state = inspect_custom_gui(shader)
    attrs = {item["type"]: item for item in state["properties"][0]["attributes"]}
    assert attrs["ASECLIFoldout"]["text"] == "基础参数"
    assert attrs["ASECLITooltip"]["text"] == "变量名：_BaseColor\n默认值：(0.5, 0.5, 0.5, 1)"
    assert attrs["ASECLIHelpBox"]["text"] == "请按项目规范设置"
    removed = remove_property_metadata_attribute(graph, "10", "ASECLITooltip")
    assert len(removed["removed"]) == 1
    assert graph.node_by_id("10").raw_fields[-3] == "2"


def test_asecli_gui_editor_writes_its_own_foldout_tooltip_and_helpbox_protocol():
    shader = AseFile.from_text(sample_shader(ASECLI_GUI_EDITOR))
    graph = shader.graph
    set_property_metadata_attribute(graph, "10", semantic_attribute("ASECLIFoldout", "基础参数"))
    set_property_metadata_attribute(graph, "10", semantic_attribute("ASECLITooltip", "基础颜色"))
    set_property_metadata_attribute(graph, "10", semantic_attribute("ASECLIHelpBox", "控制最终固有色。"))
    state = inspect_custom_gui(shader)
    assert state["editor"]["graph"] == ASECLI_GUI_EDITOR
    attributes = {item["type"]: item["text"] for item in state["properties"][0]["attributes"]}
    assert attributes == {
        "ASECLIFoldout": "基础参数",
        "ASECLITooltip": "基础颜色",
        "ASECLIHelpBox": "控制最终固有色。",
    }


def test_compiled_property_metadata_sync_preserves_unrelated_attributes():
    text = sample_shader(ASECLI_GUI_EDITOR).replace(
        "\t\t_BaseColor(\"基础颜色\", Color) = (1,1,1,1)",
        "\t\t[HDR] [HelpBoxMzgui(Old)] _BaseColor(\"基础颜色\", Color) = (1,1,1,1)",
    )
    shader = AseFile.from_text(fix_checksum(text))
    set_property_metadata_attribute(
        shader.graph, "10", semantic_attribute("ASECLIFoldout", "基础参数")
    )
    set_property_metadata_attribute(
        shader.graph, "10", semantic_attribute("ASECLIHelpBox", "控制最终固有色。")
    )

    changes = sync_compiled_property_metadata(shader)

    assert len(changes) == 1
    declaration = next(line for line in shader.prefix.splitlines() if "_BaseColor(" in line)
    assert "[HDR]" in declaration
    assert "[ASECLIFoldout(" in declaration
    assert "[ASECLIHelpBox(" in declaration
    assert "HelpBoxMzgui" not in declaration


def test_recompile_cli_restores_metadata_discarded_by_editor_save(tmp_path, monkeypatch, capsys):
    from asecli.cli.main import app

    path = tmp_path / "restore.shader"
    compiled = sample_shader(ASECLI_GUI_EDITOR).replace(
        "\t\t_BaseColor(\"基础颜色\", Color) = (1,1,1,1)",
        "\t\t_BaseColor(\"基础颜色\", Color) = (1,1,1,1)",
    )
    shader = AseFile.from_text(fix_checksum(compiled))
    set_property_metadata_attribute(
        shader.graph, "10", semantic_attribute("ASECLIFoldout", "基础参数")
    )
    set_property_metadata_attribute(
        shader.graph, "10", semantic_attribute("ASECLIHelpBox", "控制最终固有色。")
    )
    path.write_text(fix_checksum(shader.serialize()), encoding="utf-8")

    def fake_recompile(file, **kwargs):
        path.write_text(fix_checksum(compiled), encoding="utf-8")
        return {"saved": True, "changed": True}

    monkeypatch.setattr("asecli.cli.commands.recompile_via_mcp", fake_recompile)
    assert app(["recompile", str(path)]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["data"]["metadata_restored"] == 2
    restored = AseFile.from_path(path)
    attrs = {
        item["type"]: item
        for item in inspect_custom_gui(restored)["properties"][0]["attributes"]
    }
    assert attrs["ASECLIFoldout"]["text"] == "基础参数"
    assert attrs["ASECLIHelpBox"]["text"] == "控制最终固有色。"
    declaration = next(line for line in restored.prefix.splitlines() if "_BaseColor(" in line)
    assert "[ASECLIFoldout(" in declaration
    assert "[ASECLIHelpBox(" in declaration


def test_rejects_property_metadata_on_non_property_node():
    graph = AseFile.from_text(sample_shader(ASECLI_GUI_EDITOR)).graph
    with pytest.raises(ValueError, match="not an exported PropertyNode"):
        set_property_metadata_attribute(graph, "11", semantic_attribute("ASECLITooltip", "提示"))


@pytest.mark.parametrize(
    "bad",
    [
        "MZGUI.MZGUI;Injected",
        'MZGUI.MZGUI\"',
        "MZGUI.MZGUI\nInjected",
    ],
)
def test_cli_rejects_custom_editor_injection_as_single_json(tmp_path, bad):
    path = tmp_path / "bad.shader"
    path.write_text(sample_shader(), encoding="utf-8")
    code, payload = run_cli("custom-gui", str(path), "--editor", bad, "--write")
    assert code == 2
    assert payload["ok"] is False
    assert payload["error"]["code"] == "CUSTOM_GUI_ERROR"
    assert not path.with_suffix(".shader.bak").exists()


def test_cli_dry_run_is_unchanged_and_requires_explicit_asecli_editor(tmp_path):
    path = tmp_path / "dry.shader"
    path.write_text(sample_shader(), encoding="utf-8")
    before = hashlib.sha256(path.read_bytes()).hexdigest()
    code, payload = run_cli("custom-gui", str(path), "--node", "10", "--tooltip", "悬停提示")
    assert code == 2
    assert payload["error"]["code"] == "CUSTOM_GUI_ERROR"
    code, payload = run_cli(
        "custom-gui",
        str(path),
        "--editor",
        ASECLI_GUI_EDITOR,
        "--node",
        "10",
        "--tooltip",
        "悬停提示",
        "--group",
        "基础参数",
    )
    assert code == 0 and payload["data"]["written"] is False
    assert payload["data"]["requires_recompile"] is True
    assert hashlib.sha256(path.read_bytes()).hexdigest() == before
    assert not path.with_suffix(".shader.bak").exists()


def test_cli_write_is_recoverable_rechecks_checksum_and_roundtrips(tmp_path):
    path = tmp_path / "write.shader"
    original = sample_shader()
    path.write_text(original, encoding="utf-8")
    code, payload = run_cli(
        "custom-gui",
        str(path),
        "--editor",
        ASECLI_GUI_EDITOR,
        "--node",
        "10",
        "--tooltip",
        "颜色强度提示",
        "--group",
        "颜色设置",
        "--help-box",
        "控制材质的基础颜色。",
        "--write",
    )
    assert code == 0 and payload["data"]["written"] is True
    assert path.with_suffix(".shader.bak").read_text(encoding="utf-8") == original
    ok, _, _ = verify_checksum(path.read_text(encoding="utf-8"))
    assert ok is True
    written = AseFile.from_path(path)
    assert written.serialize() == path.read_text(encoding="utf-8")
    state = inspect_custom_gui(written)
    assert state["editor"]["consistent"] is True
    attrs = {item["type"]: item for item in state["properties"][0]["attributes"]}
    assert attrs["ASECLITooltip"]["text"] == "颜色强度提示"
    assert attrs["ASECLIFoldout"]["text"] == "颜色设置"


def test_cli_can_select_builtin_gui_and_add_annotations_in_one_operation(tmp_path):
    path = tmp_path / "builtin.shader"
    path.write_text(sample_shader(), encoding="utf-8")
    code, payload = run_cli(
        "custom-gui",
        str(path),
        "--editor",
        ASECLI_GUI_EDITOR,
        "--property",
        "_BaseColor",
        "--group",
        "基础参数",
        "--tooltip",
        "控制基础色。",
        "--help-box",
        "建议使用线性空间颜色。",
        "--write",
    )
    assert code == 0
    assert payload["data"]["state"]["editor"]["graph"] == ASECLI_GUI_EDITOR
    assert AseFile.from_path(path).graph.node_by_id("1").raw_fields[9] == ASECLI_GUI_EDITOR


def test_readme_single_property_example_selects_the_required_asecli_editor():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert (
        "asecli custom-gui Assets/Example.shader --editor "
        "ASECLI.MaterialGUI.ASECLIMaterialGUI --property _PaintColor"
    ) in readme


def test_cli_raw_attribute_add_remove_and_non_property_failure(tmp_path):
    path = tmp_path / "raw.shader"
    path.write_text(sample_shader(ASECLI_GUI_EDITOR), encoding="utf-8")
    raw = "[ASECLITooltip(#63D0#793A)]"
    code, payload = run_cli(
        "custom-gui", str(path), "--node", "10", "--add-attribute", raw,
        "--help-box", "控制材质的基础颜色。", "--write"
    )
    assert code == 0
    assert raw in AseFile.from_path(path).graph.node_by_id("10").raw_fields
    code, payload = run_cli(
        "custom-gui", str(path), "--node", "10", "--remove-attribute", "ASECLITooltip", "--write"
    )
    assert code == 0
    remaining = inspect_custom_gui(AseFile.from_path(path))["properties"][0]["attributes"]
    assert [item["type"] for item in remaining] == ["ASECLIHelpBox"]
    code, payload = run_cli("custom-gui", str(path), "--node", "10", "--add-attribute", "[VectorMzgui(Four)]")
    assert code == 2 and payload["error"]["code"] == "CUSTOM_GUI_ERROR"
    code, payload = run_cli("custom-gui", str(path), "--node", "11", "--tooltip", "提示")
    assert code == 2 and payload["error"]["code"] == "CUSTOM_GUI_ERROR"


def test_cli_property_name_target_sets_help_box(tmp_path):
    path = tmp_path / "property.shader"
    path.write_text(sample_shader(ASECLI_GUI_EDITOR), encoding="utf-8")
    code, payload = run_cli(
        "custom-gui", str(path), "--property", "_BaseColor", "--help-box", "车漆颜色", "--write"
    )
    assert code == 0
    assert payload["data"]["changes"][0]["node_id"] == "10"
    attrs = inspect_custom_gui(AseFile.from_path(path))["properties"][0]["attributes"]
    assert {item["type"]: item for item in attrs}["ASECLIHelpBox"]["text"] == "车漆颜色"


def test_cli_json_spec_atomically_reorders_groups_and_explains(tmp_path):
    path = tmp_path / "spec.shader"
    spec_path = tmp_path / "material-gui.json"
    original = multi_property_shader()
    path.write_text(original, encoding="utf-8")
    spec_path.write_text(
        json.dumps(
            {
                "editor": ASECLI_GUI_EDITOR,
                "reorder": True,
                "properties": [
                    {
                        "name": "_BaseColor",
                        "display_name": "基础颜色",
                        "group": "固有色",
                        "tooltip": "变量名：_BaseColor\n默认值：(1, 1, 1, 1)",
                        "help": "控制车辆基础漆面颜色。",
                    },
                    {
                        "name": "_Contrast",
                        "display_name": "明暗对比",
                        "tooltip": "变量名：_Contrast\n默认值：1.0",
                        "help": "控制车身明暗对比度；数值越大，对比越弱。",
                    },
                    {
                        "name": "_Coat_IO",
                        "display_name": "清漆输入输出",
                        "help": "控制清漆层输入输出参数。",
                    },
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    code, payload = run_cli("custom-gui", str(path), "--spec", str(spec_path))
    assert code == 0 and payload["data"]["written"] is False, payload
    assert path.read_text(encoding="utf-8") == original
    assert not path.with_suffix(".shader.bak").exists()

    code, payload = run_cli("custom-gui", str(path), "--spec", str(spec_path), "--write")
    assert code == 0 and payload["data"]["written"] is True
    assert path.with_suffix(".shader.bak").read_text(encoding="utf-8") == original
    state = inspect_custom_gui(AseFile.from_path(path))
    properties = {item["property_name"]: item for item in state["properties"]}
    assert properties["_BaseColor"]["order_index"] == 0
    assert properties["_Contrast"]["order_index"] == 1
    assert properties["_Coat_IO"]["order_index"] == 2
    base_attrs = {item["type"]: item["text"] for item in properties["_BaseColor"]["attributes"]}
    contrast_attrs = {item["type"]: item["text"] for item in properties["_Contrast"]["attributes"]}
    assert base_attrs == {
        "ASECLIFoldout": "固有色",
        "ASECLIHelpBox": "控制车辆基础漆面颜色。",
        "ASECLITooltip": "变量名：_BaseColor\n默认值：(1, 1, 1, 1)",
    }
    assert contrast_attrs["ASECLITooltip"] == "变量名：_Contrast\n默认值：1.0"
    assert contrast_attrs["ASECLIHelpBox"].endswith("对比越弱。")
    assert verify_checksum(path.read_text(encoding="utf-8"))[0] is True


@pytest.mark.parametrize(
    "spec",
    [
        {"properties": [{"name": "_BaseColor"}, {"name": "_BaseColor"}]},
        {"properties": [{"name": "_BaseColor", "unknown": "x"}]},
        {"properties": [{"name": 7}]},
        {"properties": [{"name": "_BaseColor", "node": 10}]},
        {"reorder": "yes", "properties": [{"name": "_BaseColor"}]},
    ],
)
def test_cli_json_spec_rejects_invalid_or_duplicate_entries_atomically(tmp_path, spec):
    path = tmp_path / "invalid.shader"
    spec_path = tmp_path / "invalid.json"
    original = multi_property_shader()
    path.write_text(original, encoding="utf-8")
    spec_path.write_text(json.dumps(spec), encoding="utf-8")
    code, payload = run_cli("custom-gui", str(path), "--spec", str(spec_path), "--write")
    assert code == 2 and payload["error"]["code"] == "CUSTOM_GUI_ERROR"
    assert path.read_text(encoding="utf-8") == original
    assert not path.with_suffix(".shader.bak").exists()


def test_cli_spec_rejects_conflicts_missing_file_and_non_asecli_additions(tmp_path):
    path = tmp_path / "conflict.shader"
    path.write_text(sample_shader(), encoding="utf-8")
    spec_path = tmp_path / "spec.json"
    spec_path.write_text(json.dumps({"properties": [{"name": "_BaseColor", "help": "说明"}]}), encoding="utf-8")
    code, payload = run_cli("custom-gui", str(path), "--spec", str(spec_path), "--editor", ASECLI_GUI_EDITOR)
    assert code == 2 and payload["error"]["code"] == "USAGE_ERROR"
    code, payload = run_cli("custom-gui", str(path), "--spec", str(tmp_path / "missing.json"))
    assert code == 2 and payload["error"]["code"] == "NOT_FOUND"
    code, payload = run_cli("custom-gui", str(path), "--spec", str(spec_path), "--write")
    assert code == 2 and payload["error"]["code"] == "CUSTOM_GUI_ERROR"
    assert not path.with_suffix(".shader.bak").exists()
