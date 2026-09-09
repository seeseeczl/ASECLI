"""Internal constant textures must not become public Inspector properties."""
from types import SimpleNamespace
from asecli.cli import create_command


def test_finalize_excludes_constant_sampler(monkeypatch):
    captured = {}
    monkeypatch.setattr(create_command, 'apply_material_gui_spec', lambda graph, spec: captured.update(spec))
    monkeypatch.setattr(create_command, 'sync_compiled_property_metadata', lambda graph: None)
    monkeypatch.setattr('asecli.core.compiled_metadata.hide_known_template_compiled_only_properties', lambda *args: None)
    monkeypatch.setattr(create_command, 'require_property_presentation', lambda graph: {'valid': True})
    monkeypatch.setattr(create_command, 'fix_checksum', lambda text: text)
    def node(name, kind):
        return SimpleNamespace(property_name=name, parameter_type=kind,
                               inspector_name='颜色', tooltip='控制颜色', help=None, enabled_if=None)
    spec = SimpleNamespace(nodes=[node('_Public', 'Property'), node('_Texture', 'Constant')],
                           template=SimpleNamespace(guid='template'))
    create_command._finalize_editor_property_presentation(SimpleNamespace(serialize=lambda: ''), spec)
    assert [p['name'] for p in captured['properties']] == ['_Public']
