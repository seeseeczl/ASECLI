"""Subprocess boundary for the SGCLI public command contract."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
import shutil


class SgcliAdapter:
    def __init__(self, binary: str, mcp_url: str):
        self.binary = binary
        self.mcp_url = mcp_url

    def doctor(self):
        return self._run("sg", "doctor", "--mcp-url", self.mcp_url)

    def catalog(self):
        return self._run("sg", "catalog", "--editor", "--all", "--mcp-url", self.mcp_url)

    def configured(self, spec):
        return self._with_spec(spec, "sg", "catalog", "--editor", "--graph-spec", "{spec}",
                               "--mcp-url", self.mcp_url)

    def preview(self, target_asset, spec):
        return self._with_spec(spec, "sg", "create", str(target_asset), "--spec", "{spec}",
                               "--mcp-url", self.mcp_url)

    def precheck(self, spec, inventory, outputs=None):
        """Run the installed SGCLI's exact spec_v2.prepare without an Editor call."""
        binary = Path(shutil.which(self.binary) or self.binary).resolve()
        python = binary.parent / ("python.exe" if binary.parent.name.lower() == "scripts" else "python")
        if not python.is_file():
            raise RuntimeError(f"cannot locate the SGCLI Python runtime beside {binary}")
        code = (
            "import json,sys; from sgcli.native.spec_v2 import prepare; "
            "spec=json.load(open(sys.argv[1],encoding='utf-8')); "
            "inventory=json.load(open(sys.argv[2],encoding='utf-8')); "
            "outputs=json.loads(sys.argv[3]); prepare(spec,inventory,outputs); print('{}')"
        )
        with tempfile.TemporaryDirectory(prefix="asecli-sg-precheck-") as directory:
            root = Path(directory)
            spec_path, inventory_path = root / "spec.json", root / "inventory.json"
            spec_path.write_text(json.dumps(spec, ensure_ascii=False), encoding="utf-8")
            inventory_path.write_text(json.dumps(inventory, ensure_ascii=False), encoding="utf-8")
            process = subprocess.run(
                [str(python), "-c", code, str(spec_path), str(inventory_path), json.dumps(outputs)],
                text=True, capture_output=True, check=False,
            )
        if process.returncode != 0:
            raise RuntimeError(f"SGCLI Python precheck failed: {process.stderr.strip()[-500:]}")
        return {"validator": "sgcli.native.spec_v2.prepare", "accepted": True}

    def _with_spec(self, spec, *arguments):
        with tempfile.TemporaryDirectory(prefix="asecli-export-sg-") as directory:
            path = Path(directory) / "graph.sg.json"
            path.write_text(json.dumps(spec, ensure_ascii=False), encoding="utf-8")
            return self._run(*(str(path) if arg == "{spec}" else arg for arg in arguments))

    def _run(self, *arguments):
        try:
            process = subprocess.run([self.binary, *arguments], text=True, capture_output=True, check=False)
        except OSError as exc:
            raise RuntimeError(f"cannot execute SGCLI: {exc}") from exc
        try:
            payload = json.loads(process.stdout)
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"SGCLI returned invalid JSON: {process.stderr.strip()[:300]}") from exc
        if process.returncode != 0 or payload.get("ok") is not True:
            error = payload.get("error", {})
            raise RuntimeError(f"SGCLI {error.get('code', 'ERROR')}: {error.get('message', process.stderr.strip())}")
        data = payload.get("data")
        if not isinstance(data, dict):
            raise RuntimeError("SGCLI response data must be an object")
        return data


def validate_schema(spec: dict, schema_path=None):
    path = _schema_path(schema_path)
    try:
        from jsonschema import Draft202012Validator
    except ImportError as exc:
        raise RuntimeError("export-sg requires the optional jsonschema dependency") from exc
    raw = path.read_bytes()
    schema = json.loads(raw)
    errors = sorted(Draft202012Validator(schema).iter_errors(spec), key=lambda item: list(item.path))
    if errors:
        error = errors[0]
        location = ".".join(str(item) for item in error.path) or "$"
        raise ValueError(f"SGCLI schema validation failed at {location}: {error.message}")
    return str(path), hashlib.sha256(raw).hexdigest()


def _schema_path(explicit):
    path = Path(explicit).resolve() if explicit else Path(__file__).with_name("sgcli.native.v2.schema.json")
    if not path.is_file():
        raise FileNotFoundError(f"SGCLI native v2 schema not found: {path}; pass --sg-schema")
    return path
