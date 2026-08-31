"""REG-0007: every subcommand emits valid JSON with an `ok` field; error codes are stable."""

import json
import subprocess
import sys
from pathlib import Path

FIXTURES = Path(__file__).parent / "fixtures"
SHADER = str(FIXTURES / "HLIT.shader")
FUNC = str(FIXTURES / "step-antialiasing.function.txt")
SRC = str(Path(__file__).parents[1] / "src")


def run(*args: str) -> tuple[int, dict]:
    import os

    env = dict(os.environ)
    env["PYTHONPATH"] = SRC
    proc = subprocess.run([sys.executable, "-m", "asecli.cli.main", *args], capture_output=True, text=True, env=env)
    out = proc.stdout.strip()
    assert out, f"stdout empty for {args}, stderr={proc.stderr[:300]}"
    payload = json.loads(out)
    assert "ok" in payload
    return proc.returncode, payload


def test_parse_ok():
    code, payload = run("parse", FUNC)
    assert code == 0 and payload["ok"] is True
    assert payload["data"]["node_count"] == 7


def test_set_field_dry_run_then_write(tmp_path):
    dst = tmp_path / "m.shader"
    dst.write_text((FIXTURES / "step-antialiasing.function.txt").read_text(encoding="utf-8"), encoding="utf-8")
    code, payload = run("set-field", str(dst), "--node", "5", "--field", "12", "--value", "42")
    assert code == 0 and payload["data"]["written"] is False
    code, payload = run("set-field", str(dst), "--node", "5", "--field", "12", "--value", "42", "--write")
    assert code == 0 and payload["data"]["written"] is True
    assert ";42" in dst.read_text(encoding="utf-8")


def test_validate_clean():
    code, payload = run("validate", SHADER)
    assert code == 0 and payload["ok"] is True
    assert payload["data"]["error_count"] == 0


def test_error_not_found():
    code, payload = run("parse", "/no/such/file.shader")
    assert code == 2
    assert payload["ok"] is False
    assert payload["error"]["code"] == "NOT_FOUND"


def test_connect_and_remove(tmp_path):
    dst = tmp_path / "c.shader"
    dst.write_text((FIXTURES / "step-antialiasing.function.txt").read_text(encoding="utf-8"), encoding="utf-8")
    code, payload = run("connect", str(dst), "--from", "1:0", "--to", "4:0", "--write")
    assert code == 0
    code, payload = run("remove-node", str(dst), "--node", "4", "--write")
    assert code == 0 and payload["data"]["removed_wires"] >= 1
    code, payload = run("validate", str(dst))
    assert payload["data"]["error_count"] == 0
