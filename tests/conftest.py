from pathlib import Path

import pytest

from asecli.checks import fix_checksum
from asecli.core import ASECLI_GUI_EDITOR, semantic_attribute


@pytest.fixture
def compliant_shader_path(tmp_path: Path) -> Path:
    tooltip_attribute = semantic_attribute("ASECLITooltip", "用于测试基础颜色的使用效果。")
    text = f'''Shader "HLIT"
{{
\tProperties
\t{{
\t\t{tooltip_attribute} _BaseColor("基础颜色", Color) = (1,1,1,1)
\t}}
\tSubShader {{}}
\tCustomEditor "{ASECLI_GUI_EDITOR}"
\tFallback Off
}}
/*ASEBEGIN
Version=19602
Node;AmplifyShaderEditor.TemplateMultiPassMasterNode;0;0,0;Float;False;False;-1;2;{ASECLI_GUI_EDITOR};0;1;Secondary;0
Node;AmplifyShaderEditor.TemplateMultiPassMasterNode;1;0,0;Float;False;True;-1;2;{ASECLI_GUI_EDITOR};0;1;HLIT;0
Node;AmplifyShaderEditor.ColorNode;10;100,100;Inherit;False;Property;_BaseColor;基础颜色;0;0;Create;False;1;{tooltip_attribute}
ASEEND*/
//CHKSM=PLACEHOLDER'''
    path = tmp_path / "compliant.shader"
    path.write_text(fix_checksum(text), encoding="utf-8")
    return path
