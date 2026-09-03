"""REG-0022: ASECLI custom-gui CLI write and rejection paths."""

from __future__ import annotations

import hashlib
import json

import pytest

from asecli.checks import verify_checksum
from asecli.core import (
    ASECLI_GUI_EDITOR,
    AseFile,
    inspect_custom_gui,
    semantic_attribute,
    set_property_metadata_attribute,
)
from tests.test_custom_gui import ROOT, multi_property_shader, run_cli, sample_shader

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
