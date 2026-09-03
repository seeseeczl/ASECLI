"""REG-0037: ASECLI-managed properties obey the public presentation contract."""

from __future__ import annotations

import json
import hashlib
import os
from pathlib import Path
import subprocess
import sys

import pytest

from asecli.checks import fix_checksum
from asecli.core import (
    ASECLI_GUI_EDITOR,
    AseFile,
    inspect_custom_gui,
)
from asecli.core.compiled_metadata import hide_known_template_compiled_only_properties


ROOT = Path(__file__).parents[1]
SRC = str(ROOT / "src")


def managed_shader(
    *,
    property_name: str = "_BaseColor",
    display_name: str = "基础颜色",
    help_text: str | None = "控制材质的基础颜色。",
) -> str:
    graph_attributes = ""
    compiled_attributes = ""
    if help_text is not None:
        from asecli.core import semantic_attribute

        attribute = semantic_attribute("ASECLIHelpBox", help_text)
        graph_attributes = ";1;" + attribute
        compiled_attributes = attribute + " "
    else:
        graph_attributes = ";0"
    text = f'''Shader "Tests/Presentation"
{{
\tProperties
\t{{
\t\t{compiled_attributes}{property_name}("{display_name}", Color) = (1,1,1,1)
\t}}
\tSubShader {{}}
\tCustomEditor "{ASECLI_GUI_EDITOR}"
\tFallback Off
}}
/*ASEBEGIN
Version=19602
Node;AmplifyShaderEditor.TemplateMultiPassMasterNode;0;0,0;Float;False;False;-1;2;{ASECLI_GUI_EDITOR};0;1
Node;AmplifyShaderEditor.TemplateMultiPassMasterNode;1;0,0;Float;False;True;-1;2;{ASECLI_GUI_EDITOR};0;1
Node;AmplifyShaderEditor.ColorNode;10;100,100;Inherit;False;Property;{property_name};{display_name};0;0;Create;False{graph_attributes}
ASEEND*/
//CHKSM=PLACEHOLDER'''
    return fix_checksum(text)


def run_cli(*args: str) -> tuple[int, dict]:
    env = dict(os.environ)
    env["PYTHONPATH"] = SRC
    proc = subprocess.run(
        [sys.executable, "-m", "asecli.cli.main", *args],
        capture_output=True,
        text=True,
        env=env,
    )
    return proc.returncode, json.loads(proc.stdout)


def test_custom_gui_reports_complete_property_presentation_contract():
    state = inspect_custom_gui(AseFile.from_text(managed_shader()))
    contract = state["property_presentation"]

    assert contract["contract"] == "asecli.property-presentation.v1"
    assert contract["valid"] is True
    assert contract["violations"] == []
    assert contract["tooltip"]["automatic_fields"] == [
        "property_name",
        "shader_default_value",
    ]


def test_known_template_compiled_only_properties_are_hidden_without_hiding_unknowns():
    text = managed_shader().replace(
        "\t}\n\tSubShader",
        '\t\t_TessValue("Max Tessellation", Range(1, 32)) = 16\n'
        '\t\t_UserOwned("User Owned", Float) = 1\n'
        "\t}\n\tSubShader",
        1,
    )
    shader = AseFile.from_text(fix_checksum(text))

    changes = hide_known_template_compiled_only_properties(
        shader, "2992e84f91cbeb14eab234972e07ea9d"
    )

    assert [change["property_name"] for change in changes] == ["_TessValue"]
    assert '[HideInInspector] _TessValue("Max Tessellation"' in shader.prefix
    assert '[HideInInspector] _UserOwned' not in shader.prefix
    presentation = inspect_custom_gui(shader)["property_presentation"]
    assert presentation["reconciliation"]["compiled_only"] == ["_UserOwned"]
    assert presentation["valid"] is False


def test_managed_file_reports_missing_chinese_display_name_and_help():
    state = inspect_custom_gui(
        AseFile.from_text(managed_shader(display_name="Base Color", help_text=None))
    )

    assert state["property_presentation"]["valid"] is False
    assert state["property_presentation"]["violations"] == [
        "property:_BaseColor:display_name:chinese_required",
        "property:_BaseColor:help:chinese_required",
        "property:_BaseColor:compiled_display_name:chinese_required",
        "property:_BaseColor:compiled_help:chinese_required",
    ]


def test_managed_custom_gui_write_fails_closed_when_help_is_removed(tmp_path):
    path = tmp_path / "managed.shader"
    path.write_text(managed_shader(), encoding="utf-8")

    code, payload = run_cli(
        "custom-gui",
        str(path),
        "--property",
        "_BaseColor",
        "--clear-help-box",
        "--write",
    )

    assert code == 2
    assert payload["error"]["code"] == "PROPERTY_PRESENTATION_ERROR"
    assert inspect_custom_gui(AseFile.from_path(path))["property_presentation"]["valid"] is True


def test_managed_file_cannot_bypass_the_contract_by_clearing_its_editor(tmp_path):
    path = tmp_path / "managed.shader"
    path.write_text(managed_shader(), encoding="utf-8")

    code, payload = run_cli("custom-gui", str(path), "--clear-editor", "--write")

    assert code == 2
    assert payload["error"]["code"] == "PROPERTY_PRESENTATION_ERROR"
    assert inspect_custom_gui(AseFile.from_path(path))["property_presentation"]["valid"] is True


def test_generic_write_cannot_change_a_managed_display_name_to_english(tmp_path):
    path = tmp_path / "managed.shader"
    path.write_text(managed_shader(), encoding="utf-8")

    code, payload = run_cli(
        "set-field", str(path), "--node", "10", "--field", "8",
        "--value", "Base Color", "--write"
    )

    assert code == 2
    assert payload["error"]["code"] == "PROPERTY_PRESENTATION_ERROR"
    assert inspect_custom_gui(AseFile.from_path(path))["property_presentation"]["valid"] is True


def test_material_gui_spec_can_atomically_repair_display_name_and_help(tmp_path):
    path = tmp_path / "managed.shader"
    path.write_text(managed_shader(display_name="Base Color", help_text=None), encoding="utf-8")
    spec_path = tmp_path / "gui.json"
    spec_path.write_text(
        json.dumps(
            {
                "editor": ASECLI_GUI_EDITOR,
                "properties": [
                    {
                        "name": "_BaseColor",
                        "display_name": "基础颜色",
                        "help": "控制材质的基础颜色。",
                    }
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    code, payload = run_cli("custom-gui", str(path), "--spec", str(spec_path), "--write")

    assert code == 0, payload
    assert payload["data"]["state"]["property_presentation"]["valid"] is True
    assert '_BaseColor("基础颜色", Color)' in path.read_text(encoding="utf-8")


def test_text_create_rejects_mismatched_compiled_shell_and_donor_graph(tmp_path):
    source = tmp_path / "source.shader"
    donor = tmp_path / "donor.shader"
    output = tmp_path / "mixed.shader"
    source.write_text(managed_shader(property_name="_CasterMask", display_name="投影遮罩"), encoding="utf-8")
    donor.write_text(managed_shader(property_name="_GroundMask", display_name="地面阴影遮罩"), encoding="utf-8")

    code, payload = run_cli(
        "create", str(output), "--from", str(source), "--graph-from", str(donor)
    )

    assert code == 2
    assert payload["error"]["code"] == "PROPERTY_PRESENTATION_ERROR"
    assert not output.exists()


def test_compiled_display_name_and_help_must_match_the_graph():
    different_help = "编译区说明与图内说明不一致。"
    from asecli.core import semantic_attribute

    text = managed_shader().replace(
        '_BaseColor("基础颜色", Color)', '_BaseColor("Base Color", Color)', 1
    ).replace(
        semantic_attribute("ASECLIHelpBox", "控制材质的基础颜色。"),
        semantic_attribute("ASECLIHelpBox", different_help),
        1,
    )

    presentation = inspect_custom_gui(AseFile.from_text(text))["property_presentation"]

    assert presentation["valid"] is False
    assert presentation["inspection"] == "complete"
    assert presentation["reconciliation"] == {
        "matched": ["_BaseColor"], "graph_only": [], "compiled_only": []
    }
    assert "property:_BaseColor:compiled_display_name:chinese_required" in presentation["violations"]
    assert "property:_BaseColor:display_name:graph_compiled_mismatch" in presentation["violations"]
    assert "property:_BaseColor:help:graph_compiled_mismatch" in presentation["violations"]


@pytest.mark.parametrize(
    "corrupt",
    [
        lambda text: text.replace(
            f'CustomEditor "{ASECLI_GUI_EDITOR}"',
            f'CustomEditor "{ASECLI_GUI_EDITOR}"\n\tCustomEditor "Broken.Duplicate"',
            1,
        ),
        lambda text: text.replace("Version=19602", "Version=25000", 1),
        lambda text: text.replace("Create;False;1;[ASECLIHelpBox", "Create;False;BROKEN;[ASECLIHelpBox", 1),
    ],
)
def test_managed_generic_writes_fail_closed_when_inspection_is_incomplete(tmp_path, corrupt):
    path = tmp_path / "corrupt.shader"
    path.write_text(corrupt(managed_shader()), encoding="utf-8")
    before = hashlib.sha256(path.read_bytes()).hexdigest()

    code, payload = run_cli(
        "set-field", str(path), "--node", "10", "--field", "8",
        "--value", "BaseColor", "--write"
    )

    assert code == 2
    assert payload["error"]["code"] == "PROPERTY_PRESENTATION_ERROR"
    assert hashlib.sha256(path.read_bytes()).hexdigest() == before
