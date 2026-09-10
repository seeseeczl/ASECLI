"""SGCLI composite package compatibility at the ASECLI file boundary."""

from __future__ import annotations

import json

import pytest

from asecli.bridge.editor_spec import SpecError, load_editor_graph_spec
from tests.test_editor_create_spec import receiver_spec


def test_load_accepts_versioned_ase_package(tmp_path):
    package = {
        "schema": "sgcli.ase-package.v1",
        "graph": receiver_spec(),
        "report": {"degradations": []},
    }
    path = tmp_path / "package.json"
    path.write_text(json.dumps(package), encoding="utf-8")
    assert load_editor_graph_spec(path).version == 1


def test_removing_unknown_package_version_does_not_downgrade_to_legacy(tmp_path):
    package = {"graph": receiver_spec(), "report": {}}
    path = tmp_path / "stripped-version.json"
    path.write_text(json.dumps(package), encoding="utf-8")
    with pytest.raises(SpecError, match="requires schema"):
        load_editor_graph_spec(path)


@pytest.mark.parametrize(
    "mutate, match",
    [
        (lambda package: package.update(schema="sgcli.ase-package.v9"), "unsupported"),
        (lambda package: package.update(extra=True), "unknown keys"),
        (lambda package: package.pop("report"), "requires schema, graph and report"),
        (lambda package: package.update(report=[]), "must be objects"),
    ],
)
def test_load_rejects_invalid_ase_packages(tmp_path, mutate, match):
    package = {
        "schema": "sgcli.ase-package.v1",
        "graph": receiver_spec(),
        "report": {},
    }
    mutate(package)
    path = tmp_path / "invalid-package.json"
    path.write_text(json.dumps(package), encoding="utf-8")
    with pytest.raises(SpecError, match=match):
        load_editor_graph_spec(path)
