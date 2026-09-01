"""Compile bridge (TASK-0011): MCP for Unity primary transport."""

from .mcp_client import McpClient, McpError
from .editor_create import create_shader_via_mcp
from .editor_spec import EditorGraphSpec, SpecError, load_editor_graph_spec, route_create_backend
from .graph_inspect import measure_node_bounds_via_mcp
from .gui_support import (
    ASECLI_GUI_EDITOR,
    GUI_SUPPORT_ASSET_PATH,
    MZGUI_EDITOR,
    inspect_gui_support,
    install_gui_support,
    probe_native_mzgui_via_mcp,
)
from .recompile import recompile_via_mcp

__all__ = [
    "EditorGraphSpec",
    "ASECLI_GUI_EDITOR",
    "GUI_SUPPORT_ASSET_PATH",
    "McpClient",
    "McpError",
    "MZGUI_EDITOR",
    "SpecError",
    "create_shader_via_mcp",
    "load_editor_graph_spec",
    "inspect_gui_support",
    "install_gui_support",
    "probe_native_mzgui_via_mcp",
    "measure_node_bounds_via_mcp",
    "recompile_via_mcp",
    "route_create_backend",
]
