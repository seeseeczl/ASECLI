"""CLI boundary checks for GUI support."""

import json
import os
from pathlib import Path
import subprocess
import sys

from asecli.cli.main import build_parser


ROOT = Path(__file__).parents[1]


def run_cli(*args: str) -> tuple[int, dict]:
    env = {**os.environ, "PYTHONPATH": str(ROOT / "src")}
    process = subprocess.run(
        [sys.executable, "-m", "asecli.cli.main", *args],
        capture_output=True,
        text=True,
        env=env,
    )
    return process.returncode, json.loads(process.stdout)


def test_cli_accepts_runtime_probe_and_handoff_options():
    args = build_parser().parse_args(
        ["gui-support", "Project", "--runtime-probe", "--handoff-native"]
    )
    assert args.runtime_probe is True
    assert args.handoff_native is True


def test_project_shape_is_validated_before_any_write(tmp_path):
    project = tmp_path / "NotUnity"
    project.mkdir()
    code, payload = run_cli("gui-support", str(project), "--write")
    assert code == 2
    assert payload["error"]["code"] == "GUI_SUPPORT_ERROR"
    assert not (project / "Assets").exists()
