"""Cross-repository compatibility cannot be skipped by CI or publication."""

from pathlib import Path


ROOT = Path(__file__).parents[1]


def test_ci_and_publish_call_reusable_cross_cli_gate():
    gate = (ROOT / ".github/workflows/cross-cli.yml").read_text(encoding="utf-8")
    ci = (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")
    publish = (ROOT / ".github/workflows/publish.yml").read_text(encoding="utf-8")
    assert "workflow_call:" in gate
    assert "uses: ./.github/workflows/cross-cli.yml" in ci
    assert "uses: ./.github/workflows/cross-cli.yml" in publish
    assert "needs: [verify, cross-cli]" in ci
    assert "needs: [verify, cross-cli]" in publish
    assert "--artifact-dir" in gate
    assert "cross-cli-artifacts/" in gate
