"""REG-0021: offline delivery and supply-chain gates stay executable."""

import json
import os
import subprocess
import sys
from pathlib import Path

from asecli import __version__


ROOT = Path(__file__).parents[1]


def test_ci_governance_and_supply_chain_checks_pass():
    for script in ("tools/check_ci_governance.py", "tools/supply_chain_check.py"):
        proc = subprocess.run([sys.executable, script], cwd=ROOT, capture_output=True, text=True)
        payload = json.loads(proc.stdout)
        assert proc.returncode == 0, payload
        assert payload["ok"] is True


def test_spdx_sbom_contains_artifact_checksum(tmp_path):
    dist = tmp_path / "dist"
    dist.mkdir()
    artifact = dist / "asecli-0.1.0-py3-none-any.whl"
    artifact.write_bytes(b"deterministic-test-artifact")
    output = dist / "asecli.spdx.json"
    env = dict(os.environ, SOURCE_DATE_EPOCH="1788220800")
    proc = subprocess.run(
        [sys.executable, "tools/generate_sbom.py", "--dist", str(dist), "--output", str(output)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        env=env,
    )
    assert proc.returncode == 0, proc.stderr
    sbom = json.loads(output.read_text(encoding="utf-8"))
    assert sbom["spdxVersion"] == "SPDX-2.3"
    assert "sha256:" in sbom["annotations"][0]["comment"]
    package = next(package for package in sbom["packages"] if package["name"] == "asecli")
    assert package["versionInfo"] == __version__
    assert sbom["name"] == f"asecli-{__version__}"
    assert f"/asecli-{__version__}-" in sbom["documentNamespace"]
