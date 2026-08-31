"""REG-0005 (bridge-marked): recompile via MCP requires a running editor session."""

import os

import pytest


@pytest.mark.bridge
def test_recompile_via_mcp():
    from asecli.bridge.recompile import recompile_via_mcp

    shader = os.environ.get("ASECLI_TEST_SHADER")
    if not shader:
        pytest.skip("set ASECLI_TEST_SHADER to a project shader path")
    data = recompile_via_mcp(shader)
    assert data["changed"] is True
