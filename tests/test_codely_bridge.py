"""Codely Bridge transport: framing, discovery and backend selection.

These tests use an in-process fake server so they run without an editor, while
still exercising the real frame codec and handshake handling.
"""

from __future__ import annotations

import json
import socket
import struct
import threading
import time

import pytest

from asecli.bridge.backend import BackendError, run_editor_code, select_backend
from asecli.bridge.codely_client import CodelyClient, CodelyError
from asecli.bridge.codely_probe import probe
from asecli.bridge.codely_discovery import discover_port, read_port_registry
from asecli.bridge.editor_result import EditorExecutionError, extract_payload


class FakeServer:
    """Minimal Codely-protocol server: WELCOME handshake plus framed JSON."""

    def __init__(self, responder, handshake: str = "WELCOME UNITY-TCP 1 FRAMING=1 SERVER_VERSION=2"):
        self._responder = responder
        self._handshake = handshake
        self.received: list[dict] = []
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._sock.bind(("127.0.0.1", 0))
        self._sock.listen(4)
        self.port = self._sock.getsockname()[1]
        self._thread = threading.Thread(target=self._serve, daemon=True)
        self._stop = False

    def __enter__(self) -> "FakeServer":
        self._thread.start()
        return self

    def __exit__(self, *exc_info) -> None:
        self._stop = True
        try:
            self._sock.close()
        except OSError:
            pass

    def _serve(self) -> None:
        while not self._stop:
            try:
                conn, _ = self._sock.accept()
            except OSError:
                return
            with conn:
                conn.sendall((self._handshake + "\n").encode())
                header = _recv_exactly(conn, 8)
                if header is None:
                    continue
                (size,) = struct.unpack(">Q", header)
                body = _recv_exactly(conn, size)
                if body is None:
                    continue
                request = json.loads(body.decode())
                self.received.append(request)
                reply = self._responder(request)
                if reply is None:
                    continue
                encoded = json.dumps(reply).encode()
                conn.sendall(struct.pack(">Q", len(encoded)) + encoded)


def _recv_exactly(conn, count: int):
    buffer = b""
    while len(buffer) < count:
        chunk = conn.recv(count - len(buffer))
        if not chunk:
            return None
        buffer += chunk
    return buffer


def ok_script(value: str = "done") -> dict:
    return {
        "success": True,
        "data": {
            "success": True,
            "message": "C# script executed successfully.",
            "data": {"result": value, "logs": [], "log_count": 0},
        },
    }


def script_failure(message: str) -> dict:
    return {
        "success": True,
        "data": {"success": True, "message": f"C# script execution failed: {message}"},
    }


@pytest.fixture
def registry(tmp_path):
    project = tmp_path / "Project"
    (project / "Assets").mkdir(parents=True)
    (project / "ProjectSettings").mkdir()
    return project


def write_registry(project, port: int) -> None:
    (project / ".com-unity-codely.json").write_text(
        json.dumps({"unity_port": port, "reloading": False, "reason": "ready"}),
        encoding="utf-8",
    )


def test_registry_prefers_project_file_then_legacy(registry):
    write_registry(registry, 12345)
    assert discover_port(registry) == 12345
    assert read_port_registry(registry)["reason"] == "ready"


def test_registry_absent_reports_discovery_error(registry, monkeypatch, tmp_path):
    # Isolate the home-directory fallback so a real ~/.unity-tcp cannot leak in.
    monkeypatch.setattr("pathlib.Path.home", lambda: tmp_path / "home")
    other = registry.parent / "NoRegistry"
    other.mkdir()
    assert read_port_registry(other) is None
    with pytest.raises(Exception, match="no Codely Bridge port registry"):
        discover_port(other)


def test_client_sends_big_endian_length_prefixed_json(registry):
    with FakeServer(lambda request: ok_script("ok")) as server:
        client = CodelyClient(registry, port=server.port)
        assert client.connect()["framing"] == "1"
        assert client.execute_code('return "ok";') == "ok"
        client.close()

    assert server.received == [
        {"type": "execute_csharp_script", "params": {"script": 'return "ok";'}}
    ]


def test_client_rejects_unexpected_handshake(registry):
    with FakeServer(lambda request: ok_script(), handshake="HELLO SOMETHING") as server:
        client = CodelyClient(registry, port=server.port)
        with pytest.raises(CodelyError, match="unexpected Codely handshake"):
            client.connect()


def test_compile_failure_becomes_an_error_not_a_silent_result(registry):
    with FakeServer(lambda request: script_failure("(1,1): error CS1002")) as server:
        client = CodelyClient(registry, port=server.port)
        client.connect()
        with pytest.raises(CodelyError, match="did not return a result"):
            client.execute_code("bogus")
        client.close()


def test_probe_reports_failure_instead_of_raising(registry):
    result = probe(registry, port=1)
    assert result["ok"] is False
    assert result["reason"]


def test_select_backend_honours_explicit_choice(registry):
    assert select_backend("mcp", registry)[0] == "mcp"
    assert select_backend("codely", registry)[0] == "codely"
    with pytest.raises(BackendError):
        select_backend("nonsense", registry)


def test_auto_prefers_codely_when_reachable(registry):
    with FakeServer(lambda request: ok_script("asecli-probe-ok")) as server:
        write_registry(registry, server.port)
        backend, details = select_backend("auto", registry)
        assert backend == "codely"
        assert details["probe"]["ok"] is True


def test_auto_reports_every_attempt_when_nothing_answers(registry):
    write_registry(registry, 1)  # nothing listens there
    with pytest.raises(BackendError) as excinfo:
        select_backend("auto", registry, mcp_url="http://127.0.0.1:1/mcp")
    assert "codely:" in str(excinfo.value)
    assert "mcp:" in str(excinfo.value)


def test_run_editor_code_returns_payload_and_backend(registry):
    with FakeServer(lambda request: ok_script("ASECLI_PROBE\npayload")) as server:
        write_registry(registry, server.port)
        text, used = run_editor_code(registry, "code", backend="codely")
    assert used == "codely"
    assert text == "ASECLI_PROBE\npayload"


def test_run_editor_code_rejects_unity_instance_for_codely(registry):
    with FakeServer(lambda request: ok_script()) as server:
        write_registry(registry, server.port)
        with pytest.raises(BackendError, match="unity_instance is not supported"):
            run_editor_code(registry, "code", backend="codely", unity_instance="A@1")


def test_extract_payload_handles_both_envelope_shapes():
    mcp = json.dumps({"success": True, "data": {"result": "PAYLOAD"}})
    assert extract_payload(mcp, "mcp") == "PAYLOAD"
    assert extract_payload(json.dumps({"success": True, "data": {"output": "ALT"}}), "mcp") == "ALT"
    assert extract_payload('"bare string"', "codely") == "bare string"
    assert extract_payload("plain", "codely") == "plain"


def test_extract_payload_raises_on_failed_execution():
    failed = json.dumps({"success": False, "message": "boom", "data": {"reason": "detail"}})
    with pytest.raises(EditorExecutionError, match="boom"):
        extract_payload(failed, "mcp")


# --- regression coverage for docs/adversarial-audits/2026-11-17-142104 ---


def test_home_level_registry_is_never_consulted(registry, monkeypatch, tmp_path):
    """AA-OPT-001: a user-level registry must not redirect to another project."""
    home = tmp_path / "home"
    (home / ".unity-tcp").mkdir(parents=True)
    (home / ".unity-tcp" / "unity-tcp-port.json").write_text(
        json.dumps({"unity_port": 53996, "project_path": "/elsewhere/Assets"}), encoding="utf-8"
    )
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setattr("pathlib.Path.home", lambda: home)

    assert read_port_registry(registry) is None
    with pytest.raises(Exception, match="no Codely Bridge port registry"):
        discover_port(registry)


def test_registry_for_another_project_is_rejected(registry):
    """AA-OPT-001/002: a copied registry declaring a different project is ignored."""
    (registry / ".com-unity-codely.json").write_text(
        json.dumps({"unity_port": 53996, "project_path": "/other/Project/Assets"}), encoding="utf-8"
    )
    assert read_port_registry(registry) is None
    with pytest.raises(Exception, match="belongs to"):
        discover_port(registry)


def test_registry_accepts_matching_project_path(registry):
    (registry / ".com-unity-codely.json").write_text(
        json.dumps({"unity_port": 4321, "project_path": str(registry / "Assets")}), encoding="utf-8"
    )
    assert discover_port(registry) == 4321


def test_reloading_registry_reports_retryable_error(registry):
    (registry / ".com-unity-codely.json").write_text(
        json.dumps({"unity_port": 4321, "reloading": True, "reason": "compiling"}), encoding="utf-8"
    )
    with pytest.raises(Exception, match="reloading"):
        discover_port(registry)


def test_handshake_timeout_closes_the_socket():
    """AA-OPT-003: a failed handshake must not leak the connection."""
    server = socket.socket()
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind(("127.0.0.1", 0))
    server.listen(1)
    port = server.getsockname()[1]
    threading.Thread(target=lambda: (server.accept(), threading.Event().wait(5)), daemon=True).start()

    client = CodelyClient(port=port, timeout=1)
    with pytest.raises(CodelyError, match="handshake"):
        client.connect()
    assert client._sock is None


def test_probe_honours_the_caller_timeout():
    """AA-OPT-003: the handshake must respect the probe's own budget."""
    server = socket.socket()
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind(("127.0.0.1", 0))
    server.listen(1)
    port = server.getsockname()[1]
    threading.Thread(target=lambda: (server.accept(), threading.Event().wait(10)), daemon=True).start()

    started = time.monotonic()
    result = probe(port=port, timeout=1)
    assert result["ok"] is False
    assert time.monotonic() - started < 3


def test_auto_uses_mcp_when_unity_instance_is_requested(registry, monkeypatch):
    """AA-OPT-004: Codely cannot address instances, so auto must route to mcp."""
    seen: list[str] = []

    def fake_select(requested, target, **kwargs):
        seen.append(requested)
        raise BackendError("stop-here")

    monkeypatch.setattr("asecli.bridge.backend.select_backend", fake_select)
    with pytest.raises(BackendError):
        run_editor_code(registry, "code", backend="auto", unity_instance="A@1")
    assert seen == ["mcp"]


def test_missing_payload_raises_instead_of_returning_the_envelope():
    """AA-OPT-005: an unusable payload must be loud, not silently passed on."""
    with pytest.raises(EditorExecutionError, match="empty 'result'"):
        extract_payload(json.dumps({"success": True, "data": {"result": ""}}), "mcp")
    with pytest.raises(EditorExecutionError, match="no recognisable payload"):
        extract_payload(json.dumps({"success": True, "data": {"result": {"a": 1}}}), "mcp")
