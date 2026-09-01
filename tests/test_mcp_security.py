"""REG-0017: MCP trust boundary and token handling are deny-by-default."""

import io
import json
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
