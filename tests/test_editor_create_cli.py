"""REG-0028: create backend routing and existing-target transaction gate."""

from __future__ import annotations

import json
from pathlib import Path

from asecli.cli.main import app
from asecli.core import AseFile


FIXTURES = Path(__file__).parent / "fixtures"
SHADER = FIXTURES / "HLIT.shader"
TEMPLATE_GUID = "2992e84f91cbeb14eab234972e07ea9d"


def caster_spec() -> dict:
    return {
        "version": 1,
        "template": {"guid": TEMPLATE_GUID, "shader_name": "Tests/EditorCaster"},
        "nodes": [
            {
                "alias": "mask",
                "kind": "sampler",
                "position": [-520, 20],
                "property_name": "_CasterMask",
                "inspector_name": "Caster Mask",
                "parameter_type": "Property",
            }
        ],
        "connections": [
            {"from": {"node": "mask", "port": 1}, "to": {"node": "master", "port": 2}}
        ],
    }


def _project_target(tmp_path):
    root = tmp_path / "Project"
    (root / "Assets" / "Generated").mkdir(parents=True)
    (root / "ProjectSettings").mkdir()
    return root / "Assets" / "Generated" / "Caster.shader"


def _write_spec(tmp_path):
    path = tmp_path / "graph.json"
    path.write_text(json.dumps(caster_spec()), encoding="utf-8")
    return path


def test_legacy_default_and_explicit_text_backend_are_byte_compatible(tmp_path):
    default_out = tmp_path / "default.shader"
    text_out = tmp_path / "text.shader"

    assert app(["create", str(default_out), "--from", str(SHADER), "--name", "Same"]) == 0
    assert app(["create", str(text_out), "--backend", "text", "--from", str(SHADER), "--name", "Same"]) == 0
    assert default_out.read_bytes() == text_out.read_bytes()


def test_editor_backend_requires_spec_and_rejects_text_options(tmp_path, capsys):
    target = _project_target(tmp_path)
    assert app(["create", str(target), "--backend", "editor"]) == 2
    payload = json.loads(capsys.readouterr().out)
    assert payload["error"]["code"] == "USAGE_ERROR"

    spec_path = _write_spec(tmp_path)
    assert app(["create", str(target), "--backend", "editor", "--spec", str(spec_path), "--from", str(SHADER)]) == 2
    payload = json.loads(capsys.readouterr().out)
    assert payload["error"]["code"] == "USAGE_ERROR"


def test_editor_existing_target_is_rejected_even_with_force_before_mcp(tmp_path, monkeypatch, capsys):
    target = _project_target(tmp_path)
    target.write_text("sentinel", encoding="utf-8")
    spec_path = _write_spec(tmp_path)
    called = False

    def should_not_call(*args, **kwargs):
        nonlocal called
        called = True

    monkeypatch.setattr("asecli.cli.create_command.create_shader_via_mcp", should_not_call)
    rc = app(["create", str(target), "--backend", "editor", "--spec", str(spec_path), "--force"])
    payload = json.loads(capsys.readouterr().out)
    assert rc == 2
    assert payload["error"]["code"] == "USAGE_ERROR"
    assert called is False
    assert target.read_text(encoding="utf-8") == "sentinel"


def test_auto_with_spec_uses_editor_then_parses_and_validates_result(tmp_path, monkeypatch, capsys):
    target = _project_target(tmp_path)
    spec_path = _write_spec(tmp_path)

    def fake_create(path, spec, **kwargs):
        Path(path).write_bytes(SHADER.read_bytes())
        return {
            "transport": "mcp",
            "asset_path": "Assets/Generated/Caster.shader",
            "ase_version": "1.9.6.2",
            "saved": True,
            "reloaded": True,
            "committed": True,
            "changed": True,
            "manifest": spec.expected_manifest(),
        }

    monkeypatch.setattr("asecli.cli.create_command.create_shader_via_mcp", fake_create)
    rc = app(["create", str(target), "--backend", "auto", "--spec", str(spec_path)])
    payload = json.loads(capsys.readouterr().out)

    assert rc == 0
    assert payload["data"]["backend"] == "editor"
    assert payload["data"]["saved"] is True
    assert AseFile.from_path(target).graph.nodes


def test_auto_without_spec_uses_legacy_text_path(tmp_path):
    target = tmp_path / "auto.shader"
    assert app(["create", str(target), "--backend", "auto", "--from", str(SHADER)]) == 0
    assert AseFile.from_path(target).graph.nodes


def test_editor_post_validation_failure_preserves_shader_and_meta_for_diagnosis(tmp_path, monkeypatch, capsys):
    target = _project_target(tmp_path)
    spec_path = _write_spec(tmp_path)

    def fake_invalid_create(path, spec, **kwargs):
        Path(path).write_text("not an ASE shader", encoding="utf-8")
        Path(str(path) + ".meta").write_text("temporary meta", encoding="utf-8")
        return {
            "saved": True,
            "reloaded": True,
            "committed": True,
            "transaction_nonce": "a" * 32,
            "shader_sha256": "b" * 64,
            "meta_sha256": "c" * 64,
        }

    monkeypatch.setattr("asecli.cli.create_command.create_shader_via_mcp", fake_invalid_create)
    rc = app(["create", str(target), "--backend", "editor", "--spec", str(spec_path)])
    payload = json.loads(capsys.readouterr().out)

    assert rc == 3
    assert payload["error"]["code"] == "BRIDGE_ERROR"
    assert target.read_text(encoding="utf-8") == "not an ASE shader"
    assert Path(str(target) + ".meta").read_text(encoding="utf-8") == "temporary meta"
    assert payload["data"]["cleanup"] == "skipped_untrusted_post_commit_asset"
    assert payload["data"]["transaction_nonce"] == "a" * 32


def test_editor_post_validation_race_never_deletes_replacement(tmp_path, monkeypatch, capsys):
    target = _project_target(tmp_path)
    meta = Path(str(target) + ".meta")
    spec_path = _write_spec(tmp_path)

    def fake_create(path, spec, **kwargs):
        Path(path).write_bytes(SHADER.read_bytes())
        meta.write_text("editor meta", encoding="utf-8")
        return {"transaction_nonce": "d" * 32, "shader_sha256": "e" * 64, "meta_sha256": "f" * 64}

    def replace_then_fail(path):
        Path(path).write_text("replacement from another process", encoding="utf-8")
        meta.write_text("replacement meta", encoding="utf-8")
        raise ValueError("injected post-commit race")

    monkeypatch.setattr("asecli.cli.create_command.create_shader_via_mcp", fake_create)
    monkeypatch.setattr("asecli.cli.create_command.AseFile.from_path", replace_then_fail)
    rc = app(["create", str(target), "--backend", "editor", "--spec", str(spec_path)])
    payload = json.loads(capsys.readouterr().out)
    assert rc == 3
    assert target.read_text(encoding="utf-8") == "replacement from another process"
    assert meta.read_text(encoding="utf-8") == "replacement meta"
    assert payload["data"]["cleanup"] == "skipped_untrusted_post_commit_asset"
