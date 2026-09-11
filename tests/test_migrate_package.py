"""Explicit legacy wrappers never enter the normal consumer path."""

from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

from asecli.cli.commands import CliError
from asecli.cli.migrate_package_command import cmd_migrate_package


def test_registered_v3_wrapper_extracts_canonical_bare_spec(tmp_path):
    spec = {
        "schema": "sgcli.native.v3",
        "name": "Migrated/Test",
        "nodes": [],
        "connections": [],
    }
    source = tmp_path / "WaveNoise-graph-for-sgcli.json"
    source.write_text(json.dumps({"graph": spec, "report": {}}))
    out = tmp_path / "out"
    result = cmd_migrate_package(SimpleNamespace(
        input=str(source), out_dir=str(out), extract_sg_spec=True
    ))
    spec_path = out / "WaveNoise.asecli-to-sgcli.spec.json"
    report_path = out / "WaveNoise.asecli-to-sgcli.report.json"
    receipt_path = out / "WaveNoise.asecli-to-sgcli.receipt.json"
    assert result["spec_json"] == str(spec_path)
    assert json.loads(spec_path.read_text()) == spec
    assert json.loads(report_path.read_text())["source"]["format"] == "legacy-package"
    assert result["receipt_json"] == str(receipt_path)
    assert result["legacy_format"] == "asecli-graph-report-wrapper-shape"
    assert "legacy_schema" not in result
    assert json.loads(receipt_path.read_text())["complete"] is True


def test_v2_and_unknown_legacy_wrappers_fail_closed(tmp_path):
    for index, value in enumerate((
        {"graph": {"schema": "sgcli.native.v2"}, "report": {}},
        {"graph": {}, "report": {}, "unknown": True},
    )):
        source = tmp_path / f"Legacy{index}.sg.json"
        source.write_text(json.dumps(value))
        out = tmp_path / f"out{index}"
        with pytest.raises(CliError) as raised:
            cmd_migrate_package(SimpleNamespace(
                input=str(source), out_dir=str(out), extract_sg_spec=True
            ))
        assert raised.value.code == "VALIDATION_ERROR"
        assert not (out / f"Legacy{index}.asecli-to-sgcli.spec.json").exists()
        assert (out / f"Legacy{index}.asecli-to-sgcli.report.json").is_file()
