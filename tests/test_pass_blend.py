"""Adversarial ShaderLab Forward-pass blend parsing."""

import pytest

from asecli.sg_export.pass_blend import forward_blend, forward_blend_evidence


def test_comment_decoy_cannot_replace_the_real_forward_pass():
    shader = '''
// Pass { Name "Forward"
// Blend DstColor Zero, Zero One
// }
SubShader { Pass {
    Name "Forward"
    Blend DstColor Zero, One Zero
    HLSLPROGRAM
    ENDHLSL
} }
'''

    assert forward_blend(shader) == {
        "rgb": ["DstColor", "Zero"],
        "alpha": ["One", "Zero"],
    }


def test_forward_blend_accepts_case_and_trailing_comments():
    shader = '''
subshader { pass {
    name "Forward"
    blend dstcolor zero, one zero // generated state
    hlslprogram
    ENDHLSL
} }
'''

    assert forward_blend(shader) == {
        "rgb": ["DstColor", "Zero"],
        "alpha": ["One", "Zero"],
    }


@pytest.mark.parametrize("directive", ["Blend Off", "BlendOp Add"])
def test_missing_active_blend_is_explicit_blend_off(directive: str):
    shader = f'Pass {{ Name "Forward"\n{directive}\nHLSLPROGRAM\nENDHLSL\n}}'

    assert forward_blend(shader) == {
        "rgb": ["One", "Zero"],
        "alpha": ["One", "Zero"],
    }


def test_multiple_forward_passes_are_ambiguous():
    shader = '''
Pass { Name "Forward" Blend DstColor Zero, Zero One HLSLPROGRAM ENDHLSL }
Pass { Name "Forward" Blend DstColor Zero, One Zero HLSLPROGRAM ENDHLSL }
'''

    assert forward_blend(shader) is None
    evidence = forward_blend_evidence(shader)
    assert evidence["status"] == "ambiguous"
    assert evidence["candidate_count"] == 2


def test_indexed_or_unknown_blend_factor_is_unsupported():
    shader = 'Pass { Name "Forward"\nBlend 0 SrcAlpha OneMinusSrcAlpha\nHLSLPROGRAM\nENDHLSL\n}'

    assert forward_blend(shader) is None
    assert forward_blend_evidence(shader)["status"] == "unsupported"
