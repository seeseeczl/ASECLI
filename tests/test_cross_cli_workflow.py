"""Independent delivery must not require another CLI implementation."""
import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_workflows_are_self_contained():
    for path in (ROOT / '.github/workflows').glob('*.yml'):
        text = path.read_text()
        for forbidden in ('seeseeczl/SGCLI', 'SGCLI_CANDIDATE_SHA', 'SGCLI_READ_SSH_KEY',
                          'cross-cli', 'sgcli_ref', 'sgcli-wheel'):
            assert forbidden not in text, (path, forbidden)
        assert 'tools/independent_wheel_smoke.py' in text
    publish = (ROOT / '.github/workflows/publish.yml').read_text()
    assert '  publish:\n    needs: package' in publish
    assert 'name: asecli-candidate-${{ github.sha }}' in publish


def foreign_imports(source):
    tree = ast.parse(source)
    return [name for node in ast.walk(tree)
            for name in ([n.name for n in node.names] if isinstance(node, ast.Import)
                         else [node.module or ''] if isinstance(node, ast.ImportFrom) else [])
            if name == 'sgcli' or name.startswith('sgcli.')]


def test_no_runtime_foreign_import_or_checkout_path():
    for path in (ROOT / 'src/asecli').rglob('*.py'):
        source = path.read_text()
        assert not foreign_imports(source), path
        for marker in ('GitHub/SGCLI', '../SGCLI', 'import_module("sgcli', "import_module('sgcli"):
            assert marker not in source, (path, marker)


def test_foreign_import_guard_detects_negative_examples():
    assert foreign_imports('import sgcli as helper')
    assert foreign_imports('from sgcli.contracts import native_contract')
    assert not foreign_imports('from asecli.contracts import validate_sgcli_native_spec')
