"""REG-0020: documented pytest paths and nodes remain collectable."""

import json
import subprocess
import sys
from pathlib import Path


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
