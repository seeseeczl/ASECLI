"""Minimal MCP (Model Context Protocol) streamable-HTTP client.

Speaks just enough JSON-RPC to reach an ``mcp-for-unity`` server:
initialize -> notifications/initialized -> tools/call.
Handles both plain-JSON and SSE-framed responses.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request


class McpError(RuntimeError):
    pass


class McpClient:
    def __init__(self, url: str, instance_token: str | None = None, timeout: float = 120.0):
        self.url = url
        self.instance_token = instance_token
        self.timeout = timeout
        self.session_id: str | None = None
        self._next_id = 0

    def _post(self, payload: dict) -> dict | None:
        body = json.dumps(payload).encode("utf-8")
        headers = {"Content-Type": "application/json", "Accept": "application/json, text/event-stream"}
        if self.session_id:
            headers["Mcp-Session-Id"] = self.session_id
        if self.instance_token:
            headers["X-Unity-Instance-Token"] = self.instance_token
        req = urllib.request.Request(self.url, data=body, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                sid = resp.headers.get("Mcp-Session-Id")
                if sid:
                    self.session_id = sid
                ctype = resp.headers.get("Content-Type", "")
                raw = resp.read().decode("utf-8")
        except urllib.error.HTTPError as e:
            raise McpError(f"HTTP {e.code}: {e.read().decode('utf-8', 'replace')[:300]}") from e
        except urllib.error.URLError as e:
            raise McpError(f"cannot reach MCP server at {self.url}: {e.reason}") from e
        if "text/event-stream" in ctype:
            for line in raw.splitlines():
                if line.startswith("data:"):
                    chunk = line[5:].strip()
                    if chunk and chunk != "[DONE]":
                        return json.loads(chunk)
            return None
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
            raise McpError(f"{method}: {resp['error']}")
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
        return resp.get("result", {})
