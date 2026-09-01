"""REG-0019: core exposes stable node-line parsing without private imports."""

import pytest


def test_parse_node_line_is_public_and_backward_compatible():
    from asecli.core import _parse_node_line, parse_node_line

    line = "Node;AmplifyShaderEditor.SaturateNode;99;0,0;Inherit;False"
    public = parse_node_line(line)
    legacy = _parse_node_line(line)
    assert public == legacy
    assert public.node_id == "99"
    assert public.type_name == "AmplifyShaderEditor.SaturateNode"


def test_parse_node_line_rejects_malformed_input():
    from asecli.core import parse_node_line

    with pytest.raises(ValueError, match="malformed Node line"):
        parse_node_line("Node;too-short")
