"""REG-0020: documented pytest paths and nodes remain collectable."""

import json
import subprocess
import sys
from datetime import date
from pathlib import Path

from tools.check_ci_governance import (
    NODE24_ACTION_REFS,
    _action_runtime_findings,
    _audit_supplement_findings,
    _loc_exemption_governance_findings,
    _python_loc_findings,
)


def test_regression_catalog_commands_collect():
    root = Path(__file__).parents[1]
    proc = subprocess.run(
        [sys.executable, "tools/check_regression_catalog.py"],
        cwd=root,
        capture_output=True,
        text=True,
    )
    payload = json.loads(proc.stdout)
    assert proc.returncode == 0, payload["failures"]
    assert payload["checked"] >= 15


def test_audit_supplement_has_stable_complete_module_set():
    root = Path(__file__).parents[1]
    config = json.loads((root / ".project-architect.json").read_text(encoding="utf-8"))
    assert _audit_supplement_findings(root, config) == []
    supplement = json.loads(
        (root / config["audit"]["supplement"]).read_text(encoding="utf-8")
    )
    assert len({item["id"] for item in supplement["functional_modules"]}) == 14


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

    assert _action_runtime_findings(workflow) == []
    for action, sha in NODE24_ACTION_REFS.items():
        assert f"{action}@{sha}" in workflow


def test_ci_action_runtime_gate_rejects_sha_regression():
    workflow = "\n".join(
        f"- uses: {action}@{sha}" for action, sha in NODE24_ACTION_REFS.items()
    ).replace(NODE24_ACTION_REFS["actions/checkout"], "0" * 40)

    assert _action_runtime_findings(workflow) == [
        "actions/checkout must use the approved Node 24 commit "
        f"{NODE24_ACTION_REFS['actions/checkout']}, got {'0' * 40}"
    ]
