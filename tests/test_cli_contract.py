"""REG-0007: every subcommand emits valid JSON with an `ok` field; error codes are stable."""

import json
import hashlib
import subprocess
import sys
from pathlib import Path

import pytest

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


def test_usage_error_missing_file_is_single_json_line():
    code, payload = run("parse")
    assert code == 2
    assert payload["ok"] is False
    assert payload["error"]["code"] == "USAGE_ERROR"


def test_usage_error_unknown_command_is_single_json_line():
    code, payload = run("does-not-exist")
    assert code == 2
    assert payload["ok"] is False
    assert payload["error"]["code"] == "USAGE_ERROR"


def test_usage_error_invalid_integer_is_single_json_line():
    code, payload = run("set-field", FUNC, "--node", "5", "--field", "not-an-integer", "--value", "42")
    assert code == 2
    assert payload["ok"] is False
    assert payload["error"]["code"] == "USAGE_ERROR"


@pytest.mark.parametrize(
    "command",
    [
        "parse",
        "set-field",
        "add-node",
        "connect",
        "disconnect",
        "remove-node",
        "validate",
        "fix-checksum",
        "layout",
        "custom-gui",
        "gui-support",
        "comment-group",
        "create",
        "recompile",
    ],
)
def test_every_command_usage_failure_is_single_json_line(command):
    code, payload = run(command)
    assert code == 2
    assert payload["ok"] is False
    assert payload["error"]["code"] == "USAGE_ERROR"


def test_fix_checksum_is_dry_run_by_default(tmp_path):
    dst = tmp_path / "checksum.shader"
    dst.write_text((FIXTURES / "HLIT.shader").read_text(encoding="utf-8").replace("//CHKSM=", "//CHKSM=BAD"), encoding="utf-8")
    before = hashlib.sha256(dst.read_bytes()).hexdigest()
    code, payload = run("fix-checksum", str(dst))
    assert code == 0
    assert payload["data"]["written"] is False
    assert hashlib.sha256(dst.read_bytes()).hexdigest() == before
    assert not dst.with_suffix(".shader.bak").exists()


def test_fix_checksum_write_is_explicit_and_recoverable(tmp_path):
    dst = tmp_path / "checksum.shader"
    original = (FIXTURES / "HLIT.shader").read_text(encoding="utf-8").replace("//CHKSM=", "//CHKSM=BAD")
    dst.write_text(original, encoding="utf-8")
    code, payload = run("fix-checksum", str(dst), "--write")
    assert code == 0
    assert payload["data"]["written"] is True
    assert dst.read_text(encoding="utf-8") != original
    assert dst.with_suffix(".shader.bak").read_text(encoding="utf-8") == original


def test_connect_and_remove(tmp_path):
    dst = tmp_path / "c.shader"
    dst.write_text((FIXTURES / "step-antialiasing.function.txt").read_text(encoding="utf-8"), encoding="utf-8")
    code, payload = run("disconnect", str(dst), "--from", "3:0", "--to", "4:0", "--write")
    assert code == 0
    code, payload = run("connect", str(dst), "--from", "1:0", "--to", "4:0", "--write")
    assert code == 0
    code, payload = run("remove-node", str(dst), "--node", "4", "--write")
    assert code == 0 and payload["data"]["removed_wires"] >= 1
    code, payload = run("validate", str(dst))
    assert payload["data"]["error_count"] == 0
