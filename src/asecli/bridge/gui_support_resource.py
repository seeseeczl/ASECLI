"""Packaged GUI resource composition and known upgrade identities."""

from __future__ import annotations

import hashlib
from pathlib import Path

from .resource_text import compose_resource_text


GUI_SUPPORT_ASSET_PATH = "Assets/Editor/ASECLI/ASECLIMaterialGUI.cs"
GUI_SUPPORT_RESOURCE_PARTS = (
    "asecli_material_gui.part00.cs.txt",
    "asecli_material_gui.part01.cs.txt",
    "asecli_material_gui.authoring.part00.cs.txt",
    "asecli_material_gui.authoring.store.cs.txt",
    "asecli_material_gui.authoring.part01.cs.txt",
    "asecli_material_gui.reconciliation.cs.txt",
    "asecli_material_gui.transaction.cs.txt",
    "asecli_material_gui.hydration.cs.txt",
    "asecli_material_gui.condition.cs.txt",
)
GUI_SUPPORT_SOURCE = compose_resource_text(
    "asecli.bridge", "resources", GUI_SUPPORT_RESOURCE_PARTS
)
GUI_SUPPORT_SHA256 = hashlib.sha256(GUI_SUPPORT_SOURCE.encode("utf-8")).hexdigest()
GUI_AUTHORING_RESOURCE_PARTS = GUI_SUPPORT_RESOURCE_PARTS[2:]
GUI_AUTHORING_SOURCE = compose_resource_text(
    "asecli.bridge", "resources", GUI_AUTHORING_RESOURCE_PARTS
)
GUI_AUTHORING_SHA256 = hashlib.sha256(GUI_AUTHORING_SOURCE.encode("utf-8")).hexdigest()
GUI_SUPPORT_KNOWN_PREVIOUS = {
    "cf45c7d6ad6aa79880205d73f7a6db45e20239cb312f91743056c5efa00b41b8": "0.2.0-original",
    "9541c541628b8404c66ca2c36e80af25f69960d6e1a07deabad53fd6233c5b7a": "0.3.1-material-only",
    "04a618f5b95ce564fe70e72f5ef8fe7b9c59394c53e9ec682efe27310dc4a493": "0.3.1-material-only",
    "76a092825c44ea43fa10bde7cd4185c3af1d3c26a900d90da2d8fadde150967f": "0.3.1-authoring-preview",
    "77ccadf84e3c2c1eddff343ae535c09af15402b92172e772efdf481d06c3433e": "0.3.1-authoring-preview",
    "9249b3245c01052e27bb8cf82b9e0c05e8f20ac2adfe21796a1777c4857a25ca": "0.3.1-authoring-preview",
    "738a79e7e9198dd6b21879d7d42dfad4dae6b74ef6e50e7cf17c4b3372d0e92c": "0.3.2-portable-mzgui",
    "e0fa59a9fa3ca2840f8ee2d76e03fbbb862919d2476aefec0fe7f4e64150f034": "tooltip-contract",
}


def gui_target_state(target: Path) -> tuple[str, str | None]:
    if target.is_symlink():
        return "conflict", None
    if not target.exists():
        return "absent", None
    if not target.is_file():
        return "conflict", None
    actual = hashlib.sha256(target.read_bytes()).hexdigest()
    if actual == GUI_SUPPORT_SHA256:
        return "installed", actual
    if actual == GUI_AUTHORING_SHA256:
        return "native_extension", actual
    if actual in GUI_SUPPORT_KNOWN_PREVIOUS:
        return "upgrade_available", actual
    return "conflict", actual
