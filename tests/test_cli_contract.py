"""REG-0007: every non-help invocation emits strict JSON; error codes are stable."""

import argparse
import ast
import io
import json
import hashlib
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

from asecli.cli import contract
from asecli.cli.contract import CONTRACT_VERSION, ERROR_CODES, emit_json, envelope
from asecli.cli.main import build_parser

FIXTURES = Path(__file__).parent / "fixtures"
SHADER = str(FIXTURES / "HLIT.shader")
FUNC = str(FIXTURES / "step-antialiasing.function.txt")
SRC = str(Path(__file__).parents[1] / "src")


def run(*args: str, extra_env: dict[str, str] | None = None) -> tuple[int, dict]:
    env = dict(os.environ)
    env["PYTHONPATH"] = SRC
    env.update(extra_env or {})
    proc = subprocess.run([sys.executable, "-m", "asecli.cli.main", *args], capture_output=True, text=True, env=env)
    out = proc.stdout.strip()
    assert out, f"stdout empty for {args}, stderr={proc.stderr[:300]}"
    assert len(proc.stdout.splitlines()) == 1, (proc.stdout, proc.stderr)
    payload = json.loads(out, parse_constant=_reject_nonstandard_number)
    assert "ok" in payload
    assert payload["contract_version"] == CONTRACT_VERSION
    assert isinstance(payload["cli_version"], str)
    assert "command" in payload
    return proc.returncode, payload


def _reject_nonstandard_number(value: str):
    raise ValueError(f"non-standard JSON number: {value}")


def _subcommands() -> set[str]:
    parser = build_parser()
    action = next(item for item in parser._actions if isinstance(item, argparse._SubParsersAction))
    return set(action.choices)


def test_parse_ok():
    code, payload = run("parse", FUNC)
    assert code == 0 and payload["ok"] is True
    assert payload["data"]["node_count"] == 7
    assert payload["command"] == "parse"


def test_version_is_machine_readable_json():
    code, payload = run("--version")
    assert code == 0 and payload["ok"] is True
    assert payload["command"] == "version"
    assert payload["data"]["version"] == payload["cli_version"]


@pytest.mark.parametrize("args", [("--help",), ("parse", "--help")])
def test_explicit_help_is_the_only_documented_text_stdout_exception(args):
    env = dict(os.environ)
    env["PYTHONPATH"] = SRC
    proc = subprocess.run(
        [sys.executable, "-m", "asecli.cli.main", *args], capture_output=True, text=True, env=env
    )
    assert proc.returncode == 0
    assert proc.stdout.startswith("usage: asecli")
    assert not proc.stdout.lstrip().startswith("{")


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


def test_every_parser_command_has_a_machine_contract_case(tmp_path):
    usage_failure_commands = {
        "parse", "set-field", "add-node", "connect", "disconnect", "remove-node",
        "graph-audit", "validate", "fix-checksum", "graph-review", "layout", "custom-gui",
        "gui-support", "comment-group", "create", "recompile",
    }
    assert _subcommands() == usage_failure_commands | {"install-skill"}
    for command in sorted(usage_failure_commands):
        code, payload = run(command)
        assert code == 2
        assert payload["ok"] is False
        assert payload["error"]["code"] == "USAGE_ERROR"

    code, payload = run("install-skill", "--skill-root", str(tmp_path / "skills"))
    assert code == 0 and payload["ok"] is True
    assert payload["command"] == "install-skill"


def test_ascii_stdout_preserves_unicode_error_as_complete_json():
    code, payload = run(
        "parse", "不存在.shader", extra_env={"PYTHONIOENCODING": "ascii"}
    )
    assert code == 2
    assert payload["error"] == {"code": "NOT_FOUND", "message": "file not found: 不存在.shader"}


def test_writer_rejects_non_finite_or_unserializable_data(capsys):
    for value in (float("nan"), object()):
        payload = envelope(cli_version="test", command="parse", data={"value": value})
        assert emit_json(payload, cli_version="test", command="parse") is False
        output = capsys.readouterr().out
        fallback = json.loads(output, parse_constant=_reject_nonstandard_number)
        assert fallback["ok"] is False
        assert fallback["error"]["code"] == "INTERNAL"


def test_writer_failure_uses_ascii_stderr_without_traceback(monkeypatch):
    class BrokenStdout:
        buffer = None

        def write(self, value):
            raise OSError("closed")

        def flush(self):
            raise OSError("closed")

    stderr = io.StringIO()
    monkeypatch.setattr(contract.sys, "stdout", BrokenStdout())
    monkeypatch.setattr(contract.sys, "stderr", stderr)
    payload = envelope(cli_version="test", command="parse", data={})
    assert emit_json(payload, cli_version="test", command="parse") is False
    assert stderr.getvalue() == "asecli: unable to write JSON response\n"


@pytest.mark.parametrize("value", ["nan", "inf", "-inf"])
def test_layout_rejects_non_finite_cli_gaps(value):
    code, payload = run("layout", FUNC, "--gap-x", value)
    assert code == 2
    assert payload["error"]["code"] == "USAGE_ERROR"


def test_error_code_registry_matches_implementation_and_skill_contract():
    implemented = {"INTERNAL"}
    for path in (Path(SRC) / "asecli" / "cli").glob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call) or not node.args:
                continue
            if not isinstance(node.func, ast.Name) or node.func.id != "CliError":
                continue
            code = node.args[0]
            if isinstance(code, ast.Constant) and isinstance(code.value, str):
                implemented.add(code.value)
    assert implemented == ERROR_CODES

    skill = Path(__file__).parents[1] / "skills" / "asecli" / "SKILL.md"
    error_line = next(line for line in skill.read_text(encoding="utf-8").splitlines() if line.startswith("- 错误码："))
    documented = set(re.findall(r"`([A-Z][A-Z0-9_]+)`", error_line))
    assert documented == ERROR_CODES


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
