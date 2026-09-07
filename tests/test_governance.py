"""REG-0020: documented pytest paths and nodes remain collectable."""

import json
from datetime import date
from pathlib import Path

from tools.check_ci_governance import (
    NODE24_ACTION_REFS,
    REQUIRED_CI_ACTIONS,
    _action_runtime_findings,
    _audit_supplement_findings,
    _loc_exemption_governance_findings,
    _python_loc_findings,
    _release_record_findings,
)
from tools.check_regression_catalog import (
    _parse_command,
    _unique_selectors,
    catalog_command_spans,
    catalog_commands,
)


def test_regression_catalog_parser_covers_every_pytest_span():
    root = Path(__file__).parents[1]
    catalog = root / "docs/03-quality/regression-catalog.md"
    spans = catalog_command_spans(catalog)
    commands, failures = catalog_commands(catalog)

    assert failures == []
    assert len(spans) >= 50
    assert len(commands) == len(spans)
    assert sum(command.conditional for command in commands) == 6


def test_regression_catalog_parser_handles_uv_options_and_environment():
    commands = [
        _parse_command(
            "ASECLI_PROJECT=/tmp/project uv run --frozen --python 3.12 "
            "pytest -m bridge tests/test_one.py::test_case"
        ),
        _parse_command("uv run pytest -q tests/test_two.py"),
    ]

    assert commands[0].conditional is True
    assert commands[0].selectors == ("tests/test_one.py::test_case",)
    assert commands[1].conditional is False
    assert _unique_selectors(commands) == [
        "tests/test_one.py::test_case",
        "tests/test_two.py",
    ]


def test_regression_catalog_parser_rejects_unrecognized_pytest_span(tmp_path):
    catalog = tmp_path / "catalog.md"
    catalog.write_text("| test | `pytest tests/test_missing.py` |\n", encoding="utf-8")

    commands, failures = catalog_commands(catalog)

    assert commands == []
    assert failures == [{
        "command": "pytest tests/test_missing.py",
        "detail": "pytest code span is not a supported 'uv run ... pytest' command",
    }]


def test_audit_supplement_has_stable_complete_module_set():
    root = Path(__file__).parents[1]
    config = json.loads((root / ".project-architect.json").read_text(encoding="utf-8"))
    assert _audit_supplement_findings(root, config) == []
    supplement = json.loads(
        (root / config["audit"]["supplement"]).read_text(encoding="utf-8")
    )
    assert len({item["id"] for item in supplement["functional_modules"]}) == 14


def test_released_records_have_no_pending_evidence():
    root = Path(__file__).parents[1]

    assert _release_record_findings(root) == []


def test_release_record_gate_rejects_pending_evidence(tmp_path):
    releases = tmp_path / "docs/04-delivery/releases"
    releases.mkdir(parents=True)
    record = releases / "REL-TEST.md"
    record.write_text(
        "---\ntype: release-record\nstatus: released\n---\n远端证据待回填。\n",
        encoding="utf-8",
    )

    assert _release_record_findings(tmp_path) == [
        "released record contains pending evidence: docs/04-delivery/releases/REL-TEST.md"
    ]


def test_loc_gate_classifies_tests_and_tools_and_rejects_over_limit(tmp_path):
    root = tmp_path
    (root / "src").mkdir()
    (root / "tests").mkdir()
    (root / "tools").mkdir()
    (root / "src" / "ok.py").write_text("pass\n", encoding="utf-8")
    (root / "tests" / "too_big.py").write_text("pass\n" * 5, encoding="utf-8")
    (root / "tools" / "too_big.py").write_text("pass\n" * 3, encoding="utf-8")
    config = {
        "source_roots": ["src", "tests", "tools"],
        "thresholds": {
            "source": {"warning": 2, "limit": 4},
            "test": {"warning": 4, "limit": 6},
        },
    }

    findings = _python_loc_findings(root, config)

    assert findings == [
        "tests/too_big.py has 5 lines (test strict warning limit 4)",
        "tools/too_big.py has 3 lines (source strict warning limit 2)",
    ]


def test_loc_exemption_requires_complete_unexpired_governance():
    complete = {
        "id": "EXC-TEST",
        "path": "resource.cs.txt",
        "rule": "thresholds.source.limit",
        "reason": "single transaction",
        "risk": "review scope",
        "owner": "owner",
        "approved_by": "approver",
        "created_at": "2026-09-03",
        "expires_at": "2026-10-03",
        "compensating_controls": ["real Editor E2E"],
        "exit_condition": "split after deterministic composition exists",
    }
    assert _loc_exemption_governance_findings(
        "resource.cs.txt", complete, today=date(2026, 9, 3)
    ) == []
    missing = dict(complete)
    missing.pop("owner")
    assert "resource.cs.txt loc exemption is missing owner" in _loc_exemption_governance_findings(
        "resource.cs.txt", missing, today=date(2026, 9, 3)
    )
    expired = dict(complete, created_at="2026-07-01", expires_at="2026-07-31")
    assert "resource.cs.txt loc exemption expired on 2026-07-31" in _loc_exemption_governance_findings(
        "resource.cs.txt", expired, today=date(2026, 9, 3)
    )


def test_ci_actions_use_approved_node24_commits():
    root = Path(__file__).parents[1]
    workflow = (root / ".github/workflows/ci.yml").read_text(encoding="utf-8")

    assert _action_runtime_findings(workflow, required_actions=REQUIRED_CI_ACTIONS) == []
    for action in REQUIRED_CI_ACTIONS:
        assert f"{action}@{NODE24_ACTION_REFS[action]}" in workflow


def test_publish_workflow_pins_download_artifact():
    root = Path(__file__).parents[1]
    workflow = (root / ".github/workflows/publish.yml").read_text(encoding="utf-8")

    assert _action_runtime_findings(workflow) == []
    assert (
        f"actions/download-artifact@{NODE24_ACTION_REFS['actions/download-artifact']}"
        in workflow
    )


def test_ci_action_runtime_gate_rejects_sha_regression():
    workflow = "\n".join(
        f"- uses: {action}@{sha}" for action, sha in NODE24_ACTION_REFS.items()
    ).replace(NODE24_ACTION_REFS["actions/checkout"], "0" * 40)

    assert _action_runtime_findings(workflow) == [
        "actions/checkout must use the approved Node 24 commit "
        f"{NODE24_ACTION_REFS['actions/checkout']}, got {'0' * 40}"
    ]
