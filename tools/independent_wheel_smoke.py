"""Run with a venv containing ONLY the ASECLI wheel, outside both source trees."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile


def run(cli, root, *args, ok=True):
    env = dict(os.environ, PATH=str(cli.parent))
    env.pop('PYTHONPATH', None)
    env.pop('PYTHONHOME', None)
    process = subprocess.run([str(cli), *args], cwd=root, env=env,
                             capture_output=True, text=True, timeout=30)
    value = json.loads(process.stdout)
    assert value['ok'] is ok, value
    assert process.returncode == (0 if ok else 2), process.stderr
    return value.get('data') if ok else value['error']


def shader_fixture():
    from asecli.schema import schema_for
    from asecli.export_sg import URP_UNLIT_GUID
    scalar = ['Node', 'AmplifyShaderEditor.RangedFloatNode', '10', '-400,0', 'Float',
              'False', *schema_for('AmplifyShaderEditor.RangedFloatNode')['fields']]
    master = [
        'Node', 'AmplifyShaderEditor.TemplateMultiPassMasterNode', '1', '0,0', 'Float', 'False',
        'True', '-1', '2', 'UnityEditor.ShaderGraphUnlitGUI', '0', '1', 'Export Test',
        URP_UNLIT_GUID, 'True', 'Forward', 'UniversalMaterialType=Unlit', 'RenderType=Opaque',
        'Standard', '3', 'Surface', '0', '0', '  Blend', '0', '0', 'Two Sided', '1', '0',
        'Forward Only', '0', '0', 'Cast Shadows', '1', '0', '  Use Shadow Threshold', '0', '0',
        'Receive Shadows', '1', '0', 'GPU Instancing', '1', '0', 'LOD CrossFade', '0', '0',
        'Built-in Fog', '1', '0', 'Extra Pre Pass', '0', '0', 'Tessellation', '0', '0',
    ]
    return ('Shader "Independent/Test"\n{\nProperties\n{\n}\n'
            'SubShader { Pass { Cull Back } }\n}\n/*ASEBEGIN\nVersion=19109\n'
            + ';'.join(scalar) + '\n' + ';'.join(master)
            + '\nWireConnection;1;2;10;0\nASEEND*/\n//CHKSM=TEST\n')


def main():
    assert importlib.util.find_spec('sgcli') is None, 'SGCLI must not be installed'
    cli = Path(sys.executable).parent / ('asecli.exe' if os.name == 'nt' else 'asecli')
    assert cli.is_file(), 'run using an isolated wheel installation'
    assert shutil.which('sgcli', path=str(cli.parent)) is None
    import asecli
    assert Path(asecli.__file__).resolve().is_relative_to(Path(sys.prefix).resolve()), 'not a wheel installation'
    from asecli.contracts import validate_sgcli_native_spec
    from asecli.schema_validation import SchemaValidationError
    with tempfile.TemporaryDirectory(prefix='asecli-independent-') as temporary:
        root = Path(temporary).resolve()
        (root / 'Assets').mkdir()
        (root / 'ProjectSettings').mkdir()
        source = root / 'Assets/control.shader'
        source.write_text(shader_fixture(), encoding='utf-8')
        run(cli, root, '--version')
        run(cli, root, 'contract', 'editor-graph', '--version', '3')
        result = run(cli, root, 'export-sg', str(source), '--out-dir', str(root / 'out'))
        spec_path = Path(result['spec_json'])
        spec = json.loads(spec_path.read_text())
        validate_sgcli_native_spec(spec)
        report = json.loads(Path(result['report_json']).read_text())
        receipt = json.loads(Path(result['receipt_json']).read_text())
        assert report['target']['sha256'] == hashlib.sha256(spec_path.read_bytes()).hexdigest()
        assert receipt['complete'] and report['evidence']['consumer_loaded'] == 'not_run'
        spec['unexpected'] = True
        try:
            validate_sgcli_native_spec(spec)
        except SchemaValidationError:
            pass
        else:
            raise AssertionError('unknown spec field was accepted')
        invalid = root / 'invalid.json'
        invalid.write_text('{"version":999}', encoding='utf-8')
        run(cli, root, 'contract', 'editor-graph', '--version', '3', '--spec', str(invalid), ok=False)
        source.write_text(shader_fixture().replace('UnityEditor.ShaderGraphUnlitGUI', 'Unknown.GUI'))
        error = run(cli, root, 'export-sg', str(source), '--out-dir', str(root / 'blocked'), ok=False)
        assert error['code'] == 'SG_EXPORT_BLOCKED'
        assert len(list((root / 'blocked').glob('*.report.json'))) == 1
        assert not list((root / 'blocked').glob('*.spec.json'))
        assert not list((root / 'blocked').glob('*.receipt.json'))
    print(json.dumps({'ok': True, 'standalone_wheel': True, 'consumer_executed': False}))


if __name__ == '__main__':
    main()
