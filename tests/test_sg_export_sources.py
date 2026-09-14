"""Unity asset resolution must use the meta file's own GUID."""

from pathlib import Path

import pytest

from asecli.sg_export.sources import resolve_asset
from asecli.sg_export.sources import texture_dependency, _IMPORTER_KEYS


@pytest.mark.parametrize('mutation', ['none', 'content', 'platform', 'guid'])
def test_texture_dependency_binds_content_and_complete_importer(tmp_path, mutation):
    guid = 'a' * 32
    meta = 'fileFormatVersion: 2\nguid: ' + guid + '\nTextureImporter:\n'
    meta += ''.join(f'  {key}: 0\n' for key in _IMPORTER_KEYS)
    meta += '  platformSettings:\n  - buildTarget: Android\n    overridden: 1\n    maxTextureSize: 1024\n'
    roots = [tmp_path / 'source', tmp_path / 'target']
    for root in roots:
        (root / 'Assets').mkdir(parents=True)
        (root / 'ProjectSettings').mkdir()
        (root / 'Assets/tex.png').write_bytes(b'image')
        (root / 'Assets/tex.png.meta').write_text(meta)
    shader = roots[0] / 'Assets/source.shader'
    shader.write_text('Shader {}')
    if mutation == 'content':
        (roots[1] / 'Assets/tex.png').write_bytes(b'different')
    elif mutation == 'platform':
        (roots[1] / 'Assets/tex.png.meta').write_text(meta.replace('1024', '512'))
    elif mutation == 'guid':
        (roots[1] / 'Assets/tex.png.meta').write_text(meta.replace(guid, 'b' * 32))
    if mutation != 'none':
        with pytest.raises(ValueError, match='differs|settings differ'):
            texture_dependency(shader, roots[1], guid, 'Assets/tex.png')
    else:
        evidence, kind = texture_dependency(shader, roots[1], guid, 'Assets/tex.png')
        assert kind == 'Default'
        assert evidence['snapshot']['source_sha256'] == evidence['snapshot']['target_sha256']


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
