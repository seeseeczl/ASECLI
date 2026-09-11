"""ShaderLab property and Unity asset evidence readers."""

from __future__ import annotations

import json
from pathlib import Path
import re
from typing import Any

from .model import finite, numbers


def compiled_properties(prefix: str) -> dict[str, dict[str, Any]]:
    pattern = re.compile(
        r'(?m)^\s*(?P<attrs>(?:\[[^\]\r\n]*\]\s*)*)(?P<name>[_A-Za-z]\w*)\s*\(\s*"(?P<label>(?:\\.|[^"\\])*)"\s*,\s*(?P<type>[A-Za-z]\w*\([^)]*\)|[^)\r\n]+)\s*\)\s*=\s*(?P<default>[^\r\n{]+)'
    )
    result = {}
    for match in pattern.finditer(prefix):
        raw_type, attrs = match.group("type"), match.group("attrs")
        raw_type = raw_type.strip()
        kind = ("texture2d" if raw_type == "2D" else "color" if raw_type == "Color"
                else "vector4" if raw_type == "Vector" else "float"
                if raw_type == "Float" or raw_type.startswith("Range(") else "unsupported")
        row: dict[str, Any] = {
            "display_name": match.group("label"), "type": kind,
            "hdr": "[HDR]" in attrs, "exposed": "[HideInInspector]" not in attrs,
            "attributes": re.findall(r"\[([^\]]+)\]", attrs), "shaderlab_type": raw_type,
        }
        default = match.group("default").strip()
        if kind in {"color", "vector4"}:
            row["default"] = numbers(default, 4)
        elif kind == "float":
            row["default"] = finite(default)
            if raw_type.startswith("Range("):
                row["range"] = numbers(raw_type[6:-1], 2)
        elif kind == "texture2d":
            row["default"] = None
        else:
            row["default_raw"] = default
        result[match.group("name")] = row
    return result


def property_spec(node, kind: str, compiled: dict[str, dict[str, Any]], fallback: Any) -> dict[str, Any]:
    if len(node.raw_fields) < 9:
        raise ValueError("property node is truncated")
    name = node.raw_fields[7]
    row = compiled.get(name)
    compiled_kind = "vector4" if kind in {"vector2", "vector3"} else kind
    if row is None or row["type"] != compiled_kind:
        raise ValueError(f"compiled property {name!r} is missing or has a different type")
    default = row.get("default", fallback)
    if kind in {"vector2", "vector3"}:
        width = int(kind[-1])
        if not isinstance(default, list) or len(default) != 4:
            raise ValueError(f"compiled property {name!r} has an invalid vector default")
        default = default[:width]
    result = {
        "name": name, "type": kind, "display_name": row["display_name"],
        "default": default, "exposed": row["exposed"],
    }
    if kind == "float" and "range" in row:
        result["range"] = row["range"]
    if kind == "color" and row["hdr"]:
        result["hdr"] = True
    precision = {"Float": "Single", "Half": "Half"}.get(node.raw_fields[4])
    if precision:
        result["settings"] = {"precision": precision}
    return result


def load_asset_map(path: str | Path | None) -> dict[str, str]:
    if path is None:
        return {}
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if isinstance(value, dict) and isinstance(value.get("assets"), dict):
        value = value["assets"]
    if not isinstance(value, dict) or any(not isinstance(k, str) or not isinstance(v, str) for k, v in value.items()):
        raise ValueError("asset map must be a GUID-to-project-path JSON object")
    return value


def sampler_texture_guid(node) -> str:
    """Decode the texture GUID relative to ASE's ``Create`` marker.

    Property metadata before the marker is variable-length, so an absolute
    field offset can silently read the ``-1`` object-instance sentinel instead
    of the serialized asset GUID.
    """
    try:
        create = node.raw_fields.index("Create")
    except ValueError as exc:
        raise ValueError("Texture Sample Create marker is missing") from exc
    index = create + 9
    if index >= len(node.raw_fields):
        raise ValueError("Texture Sample asset GUID is missing")
    return node.raw_fields[index].strip()


def resolve_asset(guid: str | None, target: Path, asset_map: dict[str, str]) -> str | None:
    if guid is None:
        return None
    if guid in asset_map:
        value = asset_map[guid]
        if not re.fullmatch(r"(?:Assets|Packages)/.+", value):
            raise ValueError(f"asset map path must start with Assets/ or Packages/: {value}")
        if not (target / value).is_file():
            raise ValueError(f"mapped asset does not exist: {value}")
        return value
    marker = f"guid: {guid}"
    for root_name in ("Assets", "Packages"):
        root = target / root_name
        if not root.is_dir():
            continue
        for meta in root.rglob("*.meta"):
            try:
                if marker in meta.read_text(encoding="utf-8", errors="ignore"):
                    return meta.with_suffix("").relative_to(target).as_posix()
            except OSError:
                continue
    raise ValueError(f"texture GUID {guid} is unresolved in the target project; provide --asset-map")


_IMPORTER_KEYS = (
    "textureType", "textureShape", "sRGBTexture", "enableMipMap", "filterMode",
    "aniso", "wrapU", "wrapV", "wrapW", "alphaUsage", "alphaIsTransparency",
    "textureCompression", "compressionQuality", "crunchedCompression",
)


def texture_dependency(source_shader: Path, target_project: Path, guid: str,
                       target_asset: str) -> tuple[dict[str, Any], str]:
    """Return stable source/target importer evidence and the SG sample texture type."""
    source_project = _unity_project_root(source_shader)
    if source_project is None:
        raise ValueError("source Unity project cannot be identified for texture importer verification")
    source_asset = _asset_for_guid(source_project, guid)
    if source_asset is None:
        raise ValueError(f"source texture GUID {guid} cannot be resolved for importer verification")
    target_file = target_project / target_asset
    source_settings = _texture_importer(source_asset)
    target_settings = _texture_importer(target_file)
    if source_settings != target_settings:
        differences = {
            key: {"source": source_settings.get(key), "target": target_settings.get(key)}
            for key in sorted(set(source_settings) | set(target_settings))
            if source_settings.get(key) != target_settings.get(key)
        }
        raise ValueError(f"texture importer settings differ for GUID {guid}: {differences}")
    texture_type = {0: "Default", 1: "Normal"}.get(source_settings["textureType"])
    if texture_type is None:
        raise ValueError(
            f"texture importer type {source_settings['textureType']} is not certified for Texture2D sampling"
        )
    return {
        "source_guid": guid,
        "source_asset": source_asset.relative_to(source_project).as_posix(),
        "target_asset": target_asset,
        "status": "verified_importer",
        "importer": source_settings,
    }, texture_type


def _unity_project_root(path: Path) -> Path | None:
    for parent in (path.parent, *path.parents):
        if (parent / "Assets").is_dir() and (parent / "ProjectSettings").is_dir():
            return parent
    return None


def _asset_for_guid(project: Path, guid: str) -> Path | None:
    marker = f"guid: {guid}"
    for root_name in ("Assets", "Packages"):
        root = project / root_name
        if not root.is_dir():
            continue
        for meta in sorted(root.rglob("*.meta")):
            try:
                if marker in meta.read_text(encoding="utf-8", errors="ignore"):
                    return meta.with_suffix("")
            except OSError:
                continue
    return None


def _texture_importer(asset: Path) -> dict[str, int]:
    if not asset.is_file():
        raise ValueError(f"texture asset does not exist: {asset}")
    meta = Path(f"{asset}.meta")
    if not meta.is_file():
        raise ValueError(f"texture asset has no Unity meta file: {asset}")
    text = meta.read_text(encoding="utf-8", errors="strict")
    if not re.search(r"(?m)^TextureImporter:\s*$", text):
        raise ValueError(f"asset is not imported by Unity TextureImporter: {asset}")
    result: dict[str, int] = {}
    for key in _IMPORTER_KEYS:
        matches = re.findall(rf"(?m)^\s+{re.escape(key)}:\s*(-?\d+)\s*$", text)
        if not matches:
            raise ValueError(f"TextureImporter setting {key} is unavailable: {asset}")
        # Platform blocks can repeat compression fields. The first value is the stable default setting.
        result[key] = int(matches[0])
    return result
