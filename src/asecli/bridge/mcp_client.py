"""Minimal MCP (Model Context Protocol) streamable-HTTP client.

Speaks just enough JSON-RPC to reach an ``mcp-for-unity`` server:
initialize -> notifications/initialized -> tools/call.
Handles both plain-JSON and SSE-framed responses.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request


class McpError(RuntimeError):
    pass


def redact(text: str, *secrets: str | None) -> str:
    for secret in secrets:
        if secret:
            text = text.replace(secret, "<redacted>")
    return text


def validate_mcp_url(url: str, allow_remote: bool = False) -> str:
    """Validate the MCP endpoint without resolving or contacting it."""
    try:
        parsed = urllib.parse.urlsplit(url)
        host = parsed.hostname
        parsed.port
    except ValueError as exc:
        raise McpError("invalid MCP URL") from exc
    if parsed.scheme not in {"http", "https"} or not host:
        raise McpError("MCP URL must use http or https")
    if parsed.username is not None or parsed.password is not None or parsed.query or parsed.fragment:
        raise McpError("MCP URL must not contain credentials, query parameters, or fragments")
    if host.lower() not in {"127.0.0.1", "localhost", "::1"} and not allow_remote:
        raise McpError("remote MCP URL requires --allow-remote-mcp")
    return url


class NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Never forward MCP headers or tokens to a redirect target."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def tool_text(result: dict, *secrets: str | None) -> str:
    """Return textual MCP tool output, rejecting tool-level error envelopes."""
    content = result.get("content")
    texts = []
    if isinstance(content, list):
        texts = [item.get("text", "") for item in content if isinstance(item, dict) and item.get("type") == "text"]
    summary = "\n".join(text for text in texts if text).strip()
    if result.get("isError"):
        detail = redact(summary[:300] or "no error details", *secrets)
        raise McpError(f"MCP tool failed: {detail}")
    if not summary:
        raise McpError("MCP tool returned no textual result")
    return summary


class McpClient:
    def __init__(
        self,
        url: str,
        instance_token: str | None = None,
        timeout: float = 120.0,
        allow_remote: bool = False,
    ):
        self.url = validate_mcp_url(url, allow_remote=allow_remote)
        self.instance_token = instance_token
        self.timeout = timeout
        self.session_id: str | None = None
        self._next_id = 0
        self._opener = urllib.request.build_opener(NoRedirectHandler())

    def _post(self, payload: dict) -> dict | None:
        body = json.dumps(payload).encode("utf-8")
        headers = {"Content-Type": "application/json", "Accept": "application/json, text/event-stream"}
        if self.session_id:
            headers["Mcp-Session-Id"] = self.session_id
        if self.instance_token:
            headers["X-Unity-Instance-Token"] = self.instance_token
        req = urllib.request.Request(self.url, data=body, headers=headers, method="POST")
        try:
            with self._opener.open(req, timeout=self.timeout) as resp:
                sid = resp.headers.get("Mcp-Session-Id")
                if sid:
                    self.session_id = sid
                ctype = resp.headers.get("Content-Type", "")
                raw = resp.read().decode("utf-8")
        except urllib.error.HTTPError as e:
            detail = redact(e.read().decode("utf-8", "replace")[:300], self.instance_token)
            raise McpError(f"HTTP {e.code}: {detail}") from e
        except urllib.error.URLError as e:
            detail = redact(str(e.reason), self.instance_token)
            raise McpError(f"cannot reach MCP server: {detail}") from e
        if "text/event-stream" in ctype:
            collected: list[dict] = []
            for line in raw.splitlines():
                if line.startswith("data:"):
                    chunk = line[5:].strip()
                    if chunk and chunk != "[DONE]":
                        collected.append(json.loads(chunk))
            if not collected:
                return None
            # prefer the JSON-RPC response matching our latest request id, else last frame
            for frame in reversed(collected):
                if "id" in frame:
                    return frame
            return collected[-1]
        return json.loads(raw) if raw.strip() else None

    def _rpc(self, method: str, params: dict | None = None, notify: bool = False) -> dict | None:
        self._next_id += 1
        payload: dict = {"jsonrpc": "2.0", "method": method}
        if params is not None:
            payload["params"] = params
        if not notify:
            payload["id"] = self._next_id
        resp = self._post(payload)
        if notify:
            return None
        if resp is None:
            raise McpError(f"empty response for {method}")
        if "error" in resp:
            detail = redact(str(resp["error"]), self.instance_token)
            raise McpError(f"{method}: {detail}")
        return resp

    def connect(self) -> dict:
        resp = self._rpc(
            "initialize",
            {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "asecli", "version": "0.1.0"},
            },
        )
        self._rpc("notifications/initialized", {}, notify=True)
        return resp.get("result", {}).get("serverInfo", {})

    def call_tool(self, name: str, arguments: dict) -> dict:
        resp = self._rpc("tools/call", {"name": name, "arguments": arguments})
        result = resp.get("result", {})
        tool_text(result, self.instance_token)
        return result
