"""Unity asset resolution must use the meta file's own GUID."""

from pathlib import Path

import pytest

from asecli.sg_export.sources import resolve_asset


def test_resolve_asset_ignores_guid_references_in_other_meta_files(tmp_path: Path):
    assets = tmp_path / "Assets"
    assets.mkdir()
    texture = assets / "laser.jpeg"
    texture.write_bytes(b"jpeg")
    texture.with_suffix(".jpeg.meta").write_text(
        "fileFormatVersion: 2\nguid: textureguid\nTextureImporter:\n",
        encoding="utf-8",
    )
    shader = assets / "generated.shader"
    shader.write_text("Shader {}", encoding="utf-8")
    shader.with_suffix(".shader.meta").write_text(
        "fileFormatVersion: 2\nguid: shaderguid\nShaderImporter:\n"
        "  defaultTextures:\n  - _Tex: {fileID: 2800000, guid: textureguid, type: 3}\n",
        encoding="utf-8",
    )

    assert resolve_asset("textureguid", tmp_path, {}) == "Assets/laser.jpeg"


def test_resolve_asset_rejects_duplicate_guid_owners(tmp_path: Path):
    assets = tmp_path / "Assets"
    packages = tmp_path / "Packages"
    assets.mkdir()
    packages.mkdir()
    for path in (assets / "a.png", packages / "b.png"):
        path.write_bytes(b"png")
        Path(f"{path}.meta").write_text(
            "fileFormatVersion: 2\nguid: duplicate\n", encoding="utf-8"
        )

    with pytest.raises(ValueError, match=r"duplicate.*Assets/a\.png.*Packages/b\.png"):
        resolve_asset("duplicate", tmp_path, {})


def test_resolve_asset_rejects_duplicate_guid_lines_in_one_meta(tmp_path: Path):
    assets = tmp_path / "Assets"
    assets.mkdir()
    texture = assets / "a.png"
    texture.write_bytes(b"png")
    Path(f"{texture}.meta").write_text(
        "fileFormatVersion: 2\nguid: duplicate\nguid: duplicate\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="declares GUID duplicate 2 times"):
        resolve_asset("duplicate", tmp_path, {})
