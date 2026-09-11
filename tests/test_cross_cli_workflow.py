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
    assert "needs: package" in ci
    assert "needs: package" in publish
    assert "needs: [package, cross-cli]" in publish
    assert "asecli_artifact_name: asecli-candidate-${{ github.sha }}" in ci
    assert "asecli_artifact_name: asecli-candidate-${{ github.sha }}" in publish
    assert "name: asecli-candidate-${{ github.sha }}" in publish
    assert "--artifact-dir" in gate
    assert "cross-cli-artifacts/" in gate
    assert "github.event_name != 'pull_request'" in gate
    assert "CROSS_REPO_AUTH_MISSING" in gate
    assert "CROSS_REPO_REF_INVALID" in gate
    assert "^[0-9a-fA-F]{40}$" in gate
    assert "ssh-key: ${{ secrets.sgcli_read_ssh_key }}" in gate
    assert "ref: ${{ inputs.sgcli_ref }}" in gate
    assert "sgcli_ref: main" not in ci + publish


def test_public_pull_request_path_never_checks_out_private_sgcli():
    gate = (ROOT / ".github/workflows/cross-cli.yml").read_text(encoding="utf-8")
    public_job, private_job = gate.split("  two-wheel-direct-json:", 1)
    assert "repository: seeseeczl/SGCLI" not in public_job
    assert "secrets.sgcli_read_ssh_key" not in public_job
    assert "repository: seeseeczl/SGCLI" in private_job
