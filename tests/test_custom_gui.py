"""REG-0022: ASE 1.9.6.2 CustomEditor and MZGUI operations."""

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
    read_mzgui_tail,
    remove_mzgui_attribute,
    semantic_attribute,
    set_custom_editor,
    set_mzgui_attribute,
)


ROOT = Path(__file__).parents[1]
SRC = str(ROOT / "src")
HLIT = ROOT / "tests" / "fixtures" / "HLIT.shader"


def sample_shader(editor: str = "UnityEditor.ShaderGraphLitGUI") -> str:
    text = f'''Shader "Tests/MZGUI"
{{
\tProperties {{}}
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
    text = sample_shader("MZGUI.MZGUI").replace(";基础颜色;0;0;Create", ";基础颜色;2;0;Create")
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
    state = inspect_custom_gui(AseFile.from_text(sample_shader("MZGUI.MZGUI")))
    assert state["properties"][0]["order_index"] == 0


def test_inspection_advertises_native_and_builtin_gui_providers():
    state = inspect_custom_gui(AseFile.from_text(sample_shader(ASECLI_GUI_EDITOR)))
    assert state["editor"]["graph"] == ASECLI_GUI_EDITOR
    assert state["capabilities"]["built_in_compat_editor"] == ASECLI_GUI_EDITOR
    assert set(state["capabilities"]["supported_editors_for_mzgui"]) == SUPPORTED_GUI_EDITORS


def test_custom_editor_updates_only_main_master_and_compiled_directive():
    shader = AseFile.from_text(sample_shader())
    secondary_before = shader.graph.node_by_id("0").to_line()
    change = set_custom_editor(shader, "MZGUI.MZGUI")
    assert change["main_node_id"] == "1"
    assert shader.graph.node_by_id("0").to_line() == secondary_before
    assert shader.graph.node_by_id("1").raw_fields[9] == "MZGUI.MZGUI"
    assert compiled_custom_editor(shader) == "MZGUI.MZGUI"
    assert shader.serialize().count('CustomEditor "MZGUI.MZGUI"') == 1
    set_custom_editor(shader, None)
    assert shader.graph.node_by_id("1").raw_fields[9] == ""
    assert compiled_custom_editor(shader) is None


def test_custom_editor_can_be_inserted_when_compiled_directive_is_missing():
    shader = AseFile.from_text(sample_shader().replace('\tCustomEditor "UnityEditor.ShaderGraphLitGUI"\n', ""))
    assert compiled_custom_editor(shader) is None
    set_custom_editor(shader, "MZGUI.MZGUI")
    assert compiled_custom_editor(shader) == "MZGUI.MZGUI"
    assert shader.prefix.index('CustomEditor "MZGUI.MZGUI"') < shader.prefix.index("Fallback Off")


def test_native_unicode_codecs_match_mzgui_utf16_behavior():
    text = "提示 A\n😀"
    encoded = encode_custom_unicode(text)
    assert encoded.startswith("#63D0#793A#0020#0041#000A#D83D#DE00")
    assert decode_custom_unicode(encoded) == text
    assert decode_foldout_title(encode_foldout_title("基础参数 😀")) == "基础参数 😀"


def test_reads_real_mzgui_test_foldout_tail():
    # Unmodified node line from ASE 1.9.6.2 Examples/MZGUI_Test.shader.
    body = """Version=19602
Node;AmplifyShaderEditor.IntNode;122;992,-32;Inherit;False;Property;_Int0;整数;0;0;Create;False;0;0;0;True;0;False;0;0;False;0;1;INT;0;1;[FoldoutMzgui(Foldout #6298#53e0#9875 01)]
"""
    graph = parse_graph_text(body)
    node = graph.node_by_id("122")
    tail = read_mzgui_tail(graph, node)
    assert tail.attributes == ("[FoldoutMzgui(Foldout #6298#53e0#9875 01)]",)
    assert decode_foldout_title("Foldout #6298#53e0#9875 01") == "Foldout 折叠页 01"


@pytest.mark.parametrize("graph_version", ["19109", "19602", "25000"])
def test_mzgui_tail_is_capability_probed_instead_of_locked_to_one_ase_version(graph_version):
    shader = AseFile.from_text(
        sample_shader("MZGUI.MZGUI").replace("Version=19602", f"Version={graph_version}")
    )
    set_mzgui_attribute(
        shader.graph,
        "10",
        semantic_attribute("HelpBoxMzgui", "跨版本尾部能力探测"),
    )
    tail = read_mzgui_tail(shader.graph, shader.graph.node_by_id("10"))
    assert len(tail.attributes) == 1
    assert parse_graph_text(shader.graph.serialize()).node_by_id("10").raw_fields == (
        shader.graph.node_by_id("10").raw_fields
    )


def test_unknown_property_tail_fails_closed_instead_of_guessing_an_index():
    shader = AseFile.from_text(sample_shader("MZGUI.MZGUI"))
    node = shader.graph.node_by_id("10")
    node.raw_fields[-1] = "unknown-tail-format"
    shader.graph.replace_node(node)
    with pytest.raises(ValueError, match="no valid MZGUI serialization tail"):
        set_mzgui_attribute(
            shader.graph,
            "10",
            semantic_attribute("HelpBoxMzgui", "不得猜写"),
        )


def test_group_tooltip_helpbox_add_replace_remove_and_count():
    shader = AseFile.from_text(sample_shader("MZGUI.MZGUI"))
    graph = shader.graph
    set_mzgui_attribute(graph, "10", semantic_attribute("FoldoutMzgui", "基础参数"))
    set_mzgui_attribute(graph, "10", semantic_attribute("TooltipMzgui", "变量名：_BaseColor\n默认值：(1, 1, 1, 1)"))
    set_mzgui_attribute(graph, "10", semantic_attribute("HelpBoxMzgui", "请按项目规范设置"))
    set_mzgui_attribute(graph, "10", semantic_attribute("TooltipMzgui", "变量名：_BaseColor\n默认值：(0.5, 0.5, 0.5, 1)"))
    node = graph.node_by_id("10")
    tail = read_mzgui_tail(graph, node)
    assert node.raw_fields[tail.count_index] == "3"
    state = inspect_custom_gui(shader)
    attrs = {item["type"]: item for item in state["properties"][0]["attributes"]}
    assert attrs["FoldoutMzgui"]["text"] == "基础参数"
    assert attrs["TooltipMzgui"]["text"] == "变量名：_BaseColor\n默认值：(0.5, 0.5, 0.5, 1)"
    assert attrs["HelpBoxMzgui"]["text"] == "请按项目规范设置"
    removed = remove_mzgui_attribute(graph, "10", "TooltipMzgui")
    assert len(removed["removed"]) == 1
    assert graph.node_by_id("10").raw_fields[-3] == "2"


def test_builtin_gui_editor_accepts_same_foldout_tooltip_and_helpbox_protocol():
    shader = AseFile.from_text(sample_shader(ASECLI_GUI_EDITOR))
    graph = shader.graph
    set_mzgui_attribute(graph, "10", semantic_attribute("FoldoutMzgui", "基础参数"))
    set_mzgui_attribute(graph, "10", semantic_attribute("TooltipMzgui", "基础颜色"))
    set_mzgui_attribute(graph, "10", semantic_attribute("HelpBoxMzgui", "控制最终固有色。"))
    state = inspect_custom_gui(shader)
    assert state["editor"]["graph"] == ASECLI_GUI_EDITOR
    attributes = {item["type"]: item["text"] for item in state["properties"][0]["attributes"]}
    assert attributes == {
        "FoldoutMzgui": "基础参数",
        "TooltipMzgui": "基础颜色",
        "HelpBoxMzgui": "控制最终固有色。",
    }


def test_rejects_mzgui_on_non_property_node():
    graph = AseFile.from_text(sample_shader("MZGUI.MZGUI")).graph
    with pytest.raises(ValueError, match="not an exported PropertyNode"):
        set_mzgui_attribute(graph, "11", semantic_attribute("TooltipMzgui", "提示"))


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


def test_cli_dry_run_is_unchanged_and_requires_explicit_mzgui_editor(tmp_path):
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
        "MZGUI.MZGUI",
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
        "MZGUI.MZGUI",
        "--node",
        "10",
        "--tooltip",
        "颜色强度提示",
        "--group",
        "颜色设置",
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
    assert attrs["TooltipMzgui"]["text"] == "颜色强度提示"
    assert attrs["FoldoutMzgui"]["text"] == "颜色设置"


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


def test_cli_raw_attribute_add_remove_and_non_property_failure(tmp_path):
    path = tmp_path / "raw.shader"
    path.write_text(sample_shader("MZGUI.MZGUI"), encoding="utf-8")
    raw = "[VectorMzgui(Four)]"
    code, payload = run_cli("custom-gui", str(path), "--node", "10", "--add-attribute", raw, "--write")
    assert code == 0
    assert AseFile.from_path(path).graph.node_by_id("10").raw_fields[-2:] == ["1", raw]
    code, payload = run_cli(
        "custom-gui", str(path), "--node", "10", "--remove-attribute", "VectorMzgui", "--write"
    )
    assert code == 0
    assert AseFile.from_path(path).graph.node_by_id("10").raw_fields[-1] == "0"
    code, payload = run_cli("custom-gui", str(path), "--node", "11", "--tooltip", "提示")
    assert code == 2 and payload["error"]["code"] == "CUSTOM_GUI_ERROR"


def test_cli_property_name_target_sets_help_box(tmp_path):
    path = tmp_path / "property.shader"
    path.write_text(sample_shader("MZGUI.MZGUI"), encoding="utf-8")
    code, payload = run_cli(
        "custom-gui", str(path), "--property", "_BaseColor", "--help-box", "车漆颜色", "--write"
    )
    assert code == 0
    assert payload["data"]["changes"][0]["node_id"] == "10"
    attrs = inspect_custom_gui(AseFile.from_path(path))["properties"][0]["attributes"]
    assert {item["type"]: item for item in attrs}["HelpBoxMzgui"]["text"] == "车漆颜色"


def test_cli_json_spec_atomically_reorders_groups_and_explains(tmp_path):
    path = tmp_path / "spec.shader"
    spec_path = tmp_path / "material-gui.json"
    original = multi_property_shader()
    path.write_text(original, encoding="utf-8")
    spec_path.write_text(
        json.dumps(
            {
                "editor": "MZGUI.MZGUI",
                "reorder": True,
                "properties": [
                    {
                        "name": "_BaseColor",
                        "group": "固有色",
                        "tooltip": "变量名：_BaseColor\n默认值：(1, 1, 1, 1)",
                        "help": "控制车辆基础漆面颜色。",
                    },
                    {
                        "name": "_Contrast",
                        "tooltip": "变量名：_Contrast\n默认值：1.0",
                        "help": "控制车身明暗对比度；数值越大，对比越弱。",
                    },
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    code, payload = run_cli("custom-gui", str(path), "--spec", str(spec_path))
    assert code == 0 and payload["data"]["written"] is False
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
        "FoldoutMzgui": "固有色",
        "HelpBoxMzgui": "控制车辆基础漆面颜色。",
        "TooltipMzgui": "变量名：_BaseColor\n默认值：(1, 1, 1, 1)",
    }
    assert contrast_attrs["TooltipMzgui"] == "变量名：_Contrast\n默认值：1.0"
    assert contrast_attrs["HelpBoxMzgui"].endswith("对比越弱。")
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


def test_cli_spec_rejects_conflicts_missing_file_and_non_mzgui_additions(tmp_path):
    path = tmp_path / "conflict.shader"
    path.write_text(sample_shader(), encoding="utf-8")
    spec_path = tmp_path / "spec.json"
    spec_path.write_text(json.dumps({"properties": [{"name": "_BaseColor", "help": "说明"}]}), encoding="utf-8")
    code, payload = run_cli("custom-gui", str(path), "--spec", str(spec_path), "--editor", "MZGUI.MZGUI")
    assert code == 2 and payload["error"]["code"] == "USAGE_ERROR"
    code, payload = run_cli("custom-gui", str(path), "--spec", str(tmp_path / "missing.json"))
    assert code == 2 and payload["error"]["code"] == "NOT_FOUND"
    code, payload = run_cli("custom-gui", str(path), "--spec", str(spec_path), "--write")
    assert code == 2 and payload["error"]["code"] == "CUSTOM_GUI_ERROR"
    assert not path.with_suffix(".shader.bak").exists()
