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
    MZGUI_EDITOR,
    SUPPORTED_GUI_EDITORS,
    compiled_custom_editor,
    decode_custom_unicode,
    decode_foldout_title,
    enable_if_attribute,
    encode_custom_unicode,
    encode_foldout_title,
    inspect_custom_gui,
    parse_enable_if_arguments,
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


def test_inspection_advertises_mzgui_as_the_portable_public_editor():
    state = inspect_custom_gui(AseFile.from_text(sample_shader(ASECLI_GUI_EDITOR)))
    assert state["editor"]["graph"] == ASECLI_GUI_EDITOR
    assert state["capabilities"]["built_in_editor"] == MZGUI_EDITOR
    assert state["capabilities"]["legacy_fallback_editor"] == ASECLI_GUI_EDITOR
    assert set(state["capabilities"]["supported_editors"]) == SUPPORTED_GUI_EDITORS


def test_legacy_fallback_editor_input_is_canonicalized_on_write():
    shader = AseFile.from_text(sample_shader())
    secondary_before = shader.graph.node_by_id("0").to_line()
    change = set_custom_editor(shader, ASECLI_GUI_EDITOR)
    assert change["main_node_id"] == "1"
    assert shader.graph.node_by_id("0").to_line() == secondary_before
    assert change["after"] == MZGUI_EDITOR
    assert shader.graph.node_by_id("1").raw_fields[9] == MZGUI_EDITOR
    assert compiled_custom_editor(shader) == MZGUI_EDITOR
    assert shader.serialize().count(f'CustomEditor "{MZGUI_EDITOR}"') == 1
    assert ASECLI_GUI_EDITOR not in shader.serialize()
    set_custom_editor(shader, None)
    assert shader.graph.node_by_id("1").raw_fields[9] == ""
    assert compiled_custom_editor(shader) is None


def test_custom_editor_can_be_inserted_when_compiled_directive_is_missing():
    shader = AseFile.from_text(sample_shader().replace('\tCustomEditor "UnityEditor.ShaderGraphLitGUI"\n', ""))
    assert compiled_custom_editor(shader) is None
    set_custom_editor(shader, ASECLI_GUI_EDITOR)
    assert compiled_custom_editor(shader) == MZGUI_EDITOR
    assert shader.prefix.index(f'CustomEditor "{MZGUI_EDITOR}"') < shader.prefix.index("Fallback Off")


def test_property_metadata_unicode_codecs_use_the_verified_utf16_format():
    text = "提示 A\n😀"
    encoded = encode_custom_unicode(text)
    assert encoded.startswith("#63D0#793A#0020#0041#000A#D83D#DE00")
    assert decode_custom_unicode(encoded) == text
    assert decode_foldout_title(encode_foldout_title("基础参数 😀")) == "基础参数 😀"


def test_conditional_enable_metadata_roundtrips_with_legacy_alias_support():
    shader = AseFile.from_text(sample_shader(ASECLI_GUI_EDITOR))
    raw = enable_if_attribute("_ReflectionSource", "Equal", 2)
    set_property_metadata_attribute(shader.graph, "10", raw)

    condition = inspect_custom_gui(shader)["properties"][0]["attributes"][0]
    assert condition["type"] == "EnableIfMzgui"
    assert condition["condition"] == {
        "property": "_ReflectionSource",
        "operator": "Equal",
        "value": 2.0,
    }
    assert parse_enable_if_arguments("_Mode,GreaterEqual,1.5")["operator"] == "GreaterEqual"

    set_property_metadata_attribute(
        shader.graph, "10", "[ASECLIEnableIf(_ReflectionSource,NotEqual,1)]"
    )
    attributes = read_property_metadata_tail(shader.graph, shader.graph.node_by_id("10")).attributes
    assert attributes == ("[ASECLIEnableIf(_ReflectionSource,NotEqual,1)]",)


def test_text_semantic_encoder_rejects_conditional_metadata():
    with pytest.raises(ValueError, match="no text semantic encoder"):
        semantic_attribute("EnableIfMzgui", "_Mode,Equal,1")


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
        semantic_attribute("ASECLITooltip", "跨版本尾部能力探测"),
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
            semantic_attribute("ASECLITooltip", "不得猜写"),
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
        "--tooltip",
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
            semantic_attribute("ASECLITooltip", "不得猜写"),
        )


def test_group_tooltip_and_optional_helpbox_add_replace_remove_and_count():
    shader = AseFile.from_text(sample_shader(ASECLI_GUI_EDITOR))
    graph = shader.graph
    set_property_metadata_attribute(graph, "10", semantic_attribute("ASECLIFoldout", "基础参数"))
    set_property_metadata_attribute(graph, "10", semantic_attribute("ASECLITooltip", "变量名：_BaseColor\n默认值：(1, 1, 1, 1)"))
    set_property_metadata_attribute(graph, "10", semantic_attribute("ASECLIHelpBox", "用户自定义说明"))
    set_property_metadata_attribute(graph, "10", semantic_attribute("ASECLITooltip", "变量名：_BaseColor\n默认值：(0.5, 0.5, 0.5, 1)"))
    node = graph.node_by_id("10")
    tail = read_property_metadata_tail(graph, node)
    assert node.raw_fields[tail.count_index] == "3"
    state = inspect_custom_gui(shader)
    attrs = {item["type"]: item for item in state["properties"][0]["attributes"]}
    assert attrs["ASECLIFoldout"]["text"] == "基础参数"
    assert attrs["ASECLITooltip"]["text"] == "变量名：_BaseColor\n默认值：(0.5, 0.5, 0.5, 1)"
    assert attrs["ASECLIHelpBox"]["text"] == "用户自定义说明"
    removed = remove_property_metadata_attribute(graph, "10", "ASECLITooltip")
    assert len(removed["removed"]) == 1
    assert graph.node_by_id("10").raw_fields[-3] == "2"


def test_asecli_gui_editor_writes_all_three_compatible_metadata_names():
    shader = AseFile.from_text(sample_shader(ASECLI_GUI_EDITOR))
    graph = shader.graph
    set_property_metadata_attribute(graph, "10", semantic_attribute("ASECLIFoldout", "基础参数"))
    set_property_metadata_attribute(graph, "10", semantic_attribute("ASECLITooltip", "基础颜色"))
    set_property_metadata_attribute(graph, "10", semantic_attribute("ASECLIHelpBox", "用户说明"))
    state = inspect_custom_gui(shader)
    assert state["editor"]["graph"] == ASECLI_GUI_EDITOR
    attributes = {item["type"]: item["text"] for item in state["properties"][0]["attributes"]}
    assert attributes == {
        "ASECLIFoldout": "基础参数",
        "ASECLITooltip": "基础颜色",
        "ASECLIHelpBox": "用户说明",
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
        shader.graph, "10", semantic_attribute("ASECLITooltip", "控制最终固有色。")
    )
    set_property_metadata_attribute(
        shader.graph, "10", semantic_attribute("ASECLIHelpBox", "用户常驻说明。")
    )

    changes = sync_compiled_property_metadata(shader)

    assert len(changes) == 1
    declaration = next(line for line in shader.prefix.splitlines() if "_BaseColor(" in line)
    assert "[HDR]" in declaration
    assert "[ASECLIFoldout(" in declaration
    assert "[ASECLITooltip(" in declaration
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
        shader.graph, "10", semantic_attribute("FoldoutMzgui", "基础参数")
    )
    set_property_metadata_attribute(
        shader.graph, "10", semantic_attribute("TooltipMzgui", "控制最终固有色。")
    )
    set_property_metadata_attribute(
        shader.graph, "10", semantic_attribute("HelpBoxMzgui", "用户常驻说明。")
    )
    set_property_metadata_attribute(
        shader.graph, "10", enable_if_attribute("_ReflectionSource", "Equal", 2)
    )
    path.write_text(fix_checksum(shader.serialize()), encoding="utf-8")

    def fake_recompile(file, **kwargs):
        path.write_text(fix_checksum(compiled), encoding="utf-8")
        return {"saved": True, "changed": True}

    imported = []
    def fake_import(file, **kwargs):
        # Import must see restored metadata, not the temporary Editor output.
        assert "TooltipMzgui" in path.read_text()
        imported.append(file)
        return {"synchronized": True}
    monkeypatch.setattr("asecli.cli.commands.import_shader_via_mcp", fake_import)
    monkeypatch.setattr("asecli.cli.commands.recompile_via_mcp", fake_recompile)
    assert app(["recompile", str(path)]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["data"]["metadata_restored"] == 4
    assert imported == [str(path)]
    assert payload["data"]["asset_import"]["synchronized"] is True
    restored = AseFile.from_path(path)
    attrs = {
        item["type"]: item
        for item in inspect_custom_gui(restored)["properties"][0]["attributes"]
    }
    assert attrs["FoldoutMzgui"]["text"] == "基础参数"
    assert attrs["TooltipMzgui"]["text"] == "控制最终固有色。"
    assert attrs["HelpBoxMzgui"]["text"] == "用户常驻说明。"
    assert attrs["EnableIfMzgui"]["condition"]["value"] == 2.0
    declaration = next(line for line in restored.prefix.splitlines() if "_BaseColor(" in line)
    assert "[FoldoutMzgui(" in declaration
    assert "[TooltipMzgui(" in declaration
    assert "[HelpBoxMzgui(" in declaration
    assert "[EnableIfMzgui(_ReflectionSource,Equal,2)]" in declaration
