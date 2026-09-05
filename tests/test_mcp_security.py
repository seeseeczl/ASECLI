"""REG-0017: MCP trust boundary and token handling are deny-by-default."""

import io
import json
import socket
import threading
import urllib.error

import pytest

from asecli.bridge.mcp_client import McpClient, McpError


@pytest.mark.parametrize("url", [
    "http://127.0.0.1:8080/mcp",
    "http://localhost:8080/mcp",
    "http://[::1]:8080/mcp",
])
def test_loopback_mcp_urls_are_allowed(url):
    from asecli.bridge.mcp_client import validate_mcp_url

    assert validate_mcp_url(url) == url


def test_remote_mcp_requires_explicit_opt_in():
    from asecli.bridge.mcp_client import validate_mcp_url

    with pytest.raises(McpError, match="remote"):
        validate_mcp_url("https://mcp.example.test/mcp")
    assert validate_mcp_url("https://mcp.example.test/mcp", allow_remote=True) == "https://mcp.example.test/mcp"


def test_legacy_fourth_positional_argument_still_enables_remote_mcp():
    client = McpClient("https://mcp.example.test/mcp", "token", 120.0, True)

    assert client.url == "https://mcp.example.test/mcp"
    assert client.timeout == 120.0
    assert client.connect_timeout == 20.0


@pytest.mark.parametrize("url", [
    "file:///tmp/mcp",
    "http://user:secret@127.0.0.1:8080/mcp",
    "http://127.0.0.1:8080/mcp?token=secret",
    "http://127.0.0.1:8080/mcp#secret",
])
def test_unsafe_mcp_url_forms_are_rejected(url):
    from asecli.bridge.mcp_client import validate_mcp_url

    with pytest.raises(McpError):
        validate_mcp_url(url, allow_remote=True)


def test_instance_token_argv_is_rejected_without_echo(monkeypatch, capsys):
    from asecli.cli.main import app

    secret = "TOP-SECRET-ARGV-VALUE"
    rc = app(["recompile", "ignored.shader", "--instance-token", secret])
    captured = capsys.readouterr()
    assert rc == 2
    assert secret not in captured.out
    assert secret not in captured.err
    assert json.loads(captured.out)["error"]["code"] == "USAGE_ERROR"


def test_instance_token_comes_from_environment(monkeypatch, capsys):
    from asecli.cli.main import app

    secret = "TOP-SECRET-ENV-VALUE"
    seen = {}

    def fake_recompile(file, **kwargs):
        seen.update(kwargs)
        return {"saved": True, "changed": False}

    monkeypatch.setenv("ASECLI_MCP_INSTANCE_TOKEN", secret)
    monkeypatch.setattr("asecli.cli.commands.recompile_via_mcp", fake_recompile)
    rc = app(["recompile", "ignored.shader"])
    output = capsys.readouterr().out
    assert rc == 0
    assert seen["instance_token"] == secret
    assert secret not in output


def test_token_is_redacted_from_cli_bridge_error(monkeypatch, capsys):
    from asecli.cli.main import app

    secret = "TOP-SECRET-ERROR-VALUE"

    def fake_recompile(file, **kwargs):
        raise McpError(f"server echoed {secret}")

    monkeypatch.setenv("ASECLI_MCP_INSTANCE_TOKEN", secret)
    monkeypatch.setattr("asecli.cli.commands.recompile_via_mcp", fake_recompile)
    rc = app(["recompile", "ignored.shader"])
    output = capsys.readouterr().out
    assert rc == 3
    assert secret not in output
    assert "<redacted>" in output


def test_redirect_handler_never_forwards_request():
    from asecli.bridge.mcp_client import NoRedirectHandler

    handler = NoRedirectHandler()
    assert handler.redirect_request(None, None, 302, "Found", {}, "https://remote.example/mcp") is None


def test_http_error_body_redacts_instance_token(monkeypatch):
    secret = "TOP-SECRET-HTTP-VALUE"
    client = McpClient("http://127.0.0.1:8080/mcp", instance_token=secret)
    error = urllib.error.HTTPError(
        client.url,
        500,
        "error",
        {},
        io.BytesIO(f"echoed {secret}".encode()),
    )
    monkeypatch.setattr(client._opener, "open", lambda *args, **kwargs: (_ for _ in ()).throw(error))
    with pytest.raises(McpError) as exc:
        client._post({"jsonrpc": "2.0", "id": 1, "method": "test"})
    assert secret not in str(exc.value)
    assert "<redacted>" in str(exc.value)


class _Headers:
    def __init__(self, content_type):
        self.content_type = content_type

    def get(self, name, default=None):
        return self.content_type if name == "Content-Type" else default


class _Response:
    def __init__(self, content_type, body):
        self.headers = _Headers(content_type)
        self.body = body.encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self):
        return self.body


def _rpc_response(monkeypatch, content_type, body):
    client = McpClient("http://127.0.0.1:8080/mcp")
    monkeypatch.setattr(client._opener, "open", lambda *args, **kwargs: _Response(content_type, body))
    return client


def test_sse_selects_current_id_instead_of_later_stale_frame(monkeypatch):
    body = (
        'data: {"jsonrpc":"2.0","id":1,"result":{"value":"current"}}\n\n'
        'data: {"jsonrpc":"2.0","id":999,"result":{"value":"stale"}}\n\n'
        "data: [DONE]\n"
    )
    client = _rpc_response(monkeypatch, "text/event-stream", body)
    response = client._rpc("demo")
    assert response["id"] == 1
    assert response["result"]["value"] == "current"


@pytest.mark.parametrize(
    "body, match",
    [
        ('data: {"jsonrpc":"2.0","id":999,"result":{}}\n', "id mismatch"),
        ('data: {"jsonrpc":"2.0","method":"notice"}\n', "id mismatch"),
        (
            'data: {"jsonrpc":"2.0","id":1,"result":{}}\n'
            'data: {"jsonrpc":"2.0","id":1,"result":{}}\n',
            "duplicate",
        ),
    ],
)
def test_sse_rejects_missing_wrong_or_duplicate_current_id(monkeypatch, body, match):
    client = _rpc_response(monkeypatch, "text/event-stream", body)
    with pytest.raises(McpError, match=match):
        client._rpc("demo")


def test_plain_json_rejects_wrong_response_id(monkeypatch):
    client = _rpc_response(
        monkeypatch,
        "application/json",
        '{"jsonrpc":"2.0","id":999,"result":{"value":"stale"}}',
    )
    with pytest.raises(McpError, match="id mismatch"):
        client._rpc("demo")


def test_connect_uses_short_timeout_but_tool_calls_keep_execution_timeout(monkeypatch):
    client = McpClient(
        "http://127.0.0.1:8080/mcp",
        timeout=120.0,
        connect_timeout=20.0,
    )
    seen = []
    clock = iter([100.0, 100.0, 105.0])
    monkeypatch.setattr("asecli.bridge.mcp_client.time.monotonic", lambda: next(clock))

    def fake_post(payload, *, timeout=None):
        seen.append((payload["method"], timeout))
        if payload["method"] == "initialize":
            return {"id": payload["id"], "result": {"serverInfo": {}}}
        if payload["method"] == "notifications/initialized":
            return None
        return {
            "id": payload["id"],
            "result": {"content": [{"type": "text", "text": "done"}]},
        }

    monkeypatch.setattr(client, "_post", fake_post)
    client.connect()
    client.call_tool("execute_code", {})

    assert seen == [
        ("initialize", 20.0),
        ("notifications/initialized", 15.0),
        ("tools/call", None),
    ]


def test_connect_refuses_second_phase_after_total_budget_is_exhausted(monkeypatch):
    client = McpClient("http://127.0.0.1:8080/mcp", connect_timeout=20.0)
    seen = []
    clock = iter([100.0, 100.0, 121.0])
    monkeypatch.setattr("asecli.bridge.mcp_client.time.monotonic", lambda: next(clock))

    def fake_post(payload, *, timeout=None):
        seen.append((payload["method"], timeout))
        return {"id": payload["id"], "result": {"serverInfo": {}}}

    monkeypatch.setattr(client, "_post", fake_post)

    with pytest.raises(McpError, match="notifications/initialized") as captured:
        client.connect()

    assert seen == [("initialize", 20.0)]
    assert captured.value.data == {
        "phase": "notifications/initialized",
        "elapsed_ms": 21000,
        "budget_ms": 20000,
    }


def test_stalled_http_response_is_reported_as_structured_mcp_timeout():
    listener = socket.socket()
    listener.bind(("127.0.0.1", 0))
    listener.listen()
    port = listener.getsockname()[1]

    def stall_response():
        connection, _ = listener.accept()
        try:
            connection.recv(4096)
            threading.Event().wait(0.2)
        finally:
            connection.close()
            listener.close()

    worker = threading.Thread(target=stall_response, daemon=True)
    worker.start()
    client = McpClient(f"http://127.0.0.1:{port}/mcp", timeout=0.05)

    with pytest.raises(McpError, match="MCP demo timed out") as captured:
        client._rpc("demo")

    worker.join(timeout=1.0)
    assert captured.value.data["phase"] == "demo"
    assert captured.value.data["elapsed_ms"] >= 40
    assert captured.value.data["budget_ms"] == 50


def test_urlerror_wrapped_timeout_is_reported_as_structured_mcp_timeout(monkeypatch):
    client = McpClient("http://127.0.0.1:8080/mcp", timeout=0.05)
    error = urllib.error.URLError(TimeoutError("timed out"))
    monkeypatch.setattr(
        client._opener,
        "open",
        lambda *args, **kwargs: (_ for _ in ()).throw(error),
    )

    with pytest.raises(McpError, match="MCP demo timed out") as captured:
        client._rpc("demo")

    assert captured.value.data["phase"] == "demo"
    assert captured.value.data["budget_ms"] == 50


def test_cli_preserves_structured_mcp_timeout_and_bridge_exit_code(monkeypatch, capsys):
    from asecli.cli.main import app

    def fake_recompile(*args, **kwargs):
        raise McpError(
            "MCP initialize timed out",
            data={"phase": "initialize", "elapsed_ms": 50, "budget_ms": 50},
        )

    monkeypatch.setattr("asecli.cli.commands.recompile_via_mcp", fake_recompile)
    rc = app(["recompile", "ignored.shader"])
    payload = json.loads(capsys.readouterr().out)

    assert rc == 3
    assert payload["error"]["code"] == "BRIDGE_ERROR"
    assert payload["data"] == {
        "phase": "initialize",
        "elapsed_ms": 50,
        "budget_ms": 50,
    }
