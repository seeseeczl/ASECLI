"""Connected-Editor runtime probe for MZGUI providers."""

from __future__ import annotations

from pathlib import Path

from ._gui_project import unity_project
from .gui_provider_detection import probe_native_mzgui_for_assets
from .gui_support import GUI_SUPPORT_ASSET_PATH


def probe_native_mzgui_via_mcp(
    project_root: str | Path,
    *,
    mcp_url: str = "http://127.0.0.1:8080/mcp",
    instance_token: str | None = None,
    allow_remote_mcp: bool = False,
) -> dict:
    project = unity_project(project_root, GUI_SUPPORT_ASSET_PATH)
    return probe_native_mzgui_for_assets(
        project.assets,
        mcp_url=mcp_url,
        instance_token=instance_token,
        allow_remote_mcp=allow_remote_mcp,
    )
