"""Codely Bridge transport (``cn.tuanjie.codely.bridge``).

Frame format: an 8-byte big-endian unsigned length then UTF-8 JSON, both ways.
Requests are ``{"type": ..., "params": {...}}``.  Verified against
``cn.tuanjie.codely.bridge@1.0.66``; see
``docs/01-architecture/codely-bridge-protocol.md``.

Two server behaviours shape this client: ``FrameIOTimeoutMs`` (3000 ms) bounds a
single *read* rather than total processing, so the timeout here is generous; and
a failed compile still answers ``success: true`` with the failure in
``data.message``, which :meth:`CodelyClient.execute_code` converts to an error.
"""

from __future__ import annotations

import json
import socket
import struct
import time
from pathlib import Path

from .codely_discovery import DiscoveryError, discover_port

COMMAND_EXECUTE_SCRIPT = "execute_csharp_script"
HANDSHAKE_PREFIX = "WELCOME UNITY-TCP"
WELCOME_TIMEOUT = 10.0
DEFAULT_TIMEOUT = 180.0


class CodelyError(DiscoveryError):
    """Raised for any Codely transport or command failure."""

    def __init__(self, message: str, *, phase: str | None = None, data: dict | None = None):
        super().__init__(message)
        self.phase = phase
        self.data = data or {}


class CodelyClient:
    """Minimal Codely Bridge client mirroring the shape of :class:`McpClient`."""

    def __init__(
        self,
        project_root: str | Path | None = None,
        *,
        port: int | None = None,
        timeout: float = DEFAULT_TIMEOUT,
        host: str = "127.0.0.1",
    ):
        self._project_root = Path(project_root).resolve() if project_root else None
        self.port = port
        self.timeout = timeout
        self.host = host
        self._sock: socket.socket | None = None
        self.server_info: dict = {}

    # -- connection -----------------------------------------------------

    def connect(self) -> dict:
        if self._sock is not None:
            return self.server_info
        if self.port is None:
            if self._project_root is None:
                raise CodelyError("project_root or port is required", phase="discover")
            self.port = discover_port(self._project_root)
        try:
            sock = socket.create_connection((self.host, self.port), timeout=self.timeout)
        except OSError as exc:
            raise CodelyError(
                f"cannot reach Codely Bridge on {self.host}:{self.port}: {exc}",
                phase="connect",
            ) from exc
        sock.settimeout(self.timeout)
        self._sock = sock
        try:
            self.server_info = self._read_handshake()
        except socket.timeout as exc:
            self.close()
            raise CodelyError(
                f"Codely handshake timed out after {self.timeout:.0f}s",
                phase="handshake",
            ) from exc
        except BaseException:  # a half-open connection must not outlive failure
            self.close()
            raise
        return self.server_info

    def _read_handshake(self) -> dict:
        raw = self._recv_until(b"\n", WELCOME_TIMEOUT)
        text = raw.decode("utf-8", "replace").strip()
        if not text.startswith(HANDSHAKE_PREFIX):
            self.close()
            raise CodelyError(
                f"unexpected Codely handshake: {text[:120]!r}",
                phase="handshake",
                data={"handshake": text[:200]},
            )
        info: dict = {"handshake": text}
        for token in text.split():
            if "=" in token:
                key, _, value = token.partition("=")
                info[key.lower()] = value
        return info

    def _recv_until(self, marker: bytes, timeout: float) -> bytes:
        assert self._sock is not None
        previous = self._sock.gettimeout()
        self._sock.settimeout(min(timeout, self.timeout))
        try:
            buffer = b""
            while marker not in buffer:
                chunk = self._sock.recv(4096)
                if not chunk:
                    raise CodelyError("connection closed during handshake", phase="handshake")
                buffer += chunk
                if len(buffer) > 8192:
                    raise CodelyError("handshake exceeded 8192 bytes", phase="handshake")
            return buffer
        finally:
            self._sock.settimeout(previous)

    def close(self) -> None:
        if self._sock is not None:
            try:
                self._sock.close()
            finally:
                self._sock = None

    def __enter__(self) -> "CodelyClient":
        self.connect()
        return self

    def __exit__(self, *exc_info) -> None:
        self.close()

    # -- framing --------------------------------------------------------

    def _recv_exactly(self, count: int) -> bytes:
        assert self._sock is not None
        buffer = b""
        while len(buffer) < count:
            chunk = self._sock.recv(count - len(buffer))
            if not chunk:
                raise CodelyError(f"closed after {len(buffer)}/{count} bytes", phase="read")
            buffer += chunk
        return buffer

    def _roundtrip(self, command: str, params: dict) -> dict:
        if self._sock is None:
            self.connect()
        payload = json.dumps({"type": command, "params": params}, ensure_ascii=False).encode("utf-8")
        header = struct.pack(">Q", len(payload))
        assert self._sock is not None
        try:
            self._sock.sendall(header + payload)
            raw_header = self._recv_exactly(8)
            (size,) = struct.unpack(">Q", raw_header)
            if size > 64 * 1024 * 1024:
                raise CodelyError(f"response frame of {size} bytes exceeds 64 MiB", phase="read")
            body = self._recv_exactly(size) if size else b""
        except socket.timeout as exc:
            elapsed_ms = round(self.timeout * 1000)
            self.close()
            raise CodelyError(
                f"Codely {command} timed out after {elapsed_ms} ms",
                phase="timeout",
                data={"elapsed_ms": elapsed_ms},
            ) from exc
        except OSError as exc:
            self.close()
            raise CodelyError(f"Codely {command} failed: {exc}", phase="io") from exc
        try:
            response = json.loads(body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise CodelyError(f"Codely {command} returned malformed JSON", phase="parse") from exc
        if not isinstance(response, dict):
            raise CodelyError(f"Codely {command} returned a non-object response", phase="parse")
        return response

    # -- commands -------------------------------------------------------

    def call(self, command: str, params: dict | None = None) -> dict:
        """Send one command and return the outer response envelope."""
        response = self._roundtrip(command, params or {})
        if response.get("success") is False:
            detail = response.get("error") or response.get("message") or "command failed"
            code = response.get("code")
            raise CodelyError(
                f"Codely {command} failed: {detail}"
                + (f" (code={code})" if code else ""),
                phase="command",
                data=response.get("data") if isinstance(response.get("data"), dict) else None,
            )
        return response

    def execute_code(self, code: str) -> str:
        """Run *code* through ``execute_csharp_script`` and return its result text.

        Raises :class:`CodelyError` when the script fails to compile or run,
        which the server otherwise reports inside a successful envelope.
        """
        response = self.call(COMMAND_EXECUTE_SCRIPT, {"script": code})
        outer = response.get("data")
        if not isinstance(outer, dict):
            raise CodelyError("Codely script response is missing its data envelope", phase="command")
        if outer.get("success") is False:
            detail = outer.get("error") or outer.get("message") or "script failed"
            raise CodelyError(f"Codely script failed: {detail}", phase="command")
        inner = outer.get("data")
        if not isinstance(inner, dict) or "result" not in inner:
            message = str(outer.get("message") or "")
            raise CodelyError(
                f"Codely script did not return a result: {message[:300] or 'no message'}",
                phase="command",
                data={"message": message},
            )
        result = inner["result"]
        if result is None:
            raise CodelyError("Codely script returned a null result", phase="command")
        return result if isinstance(result, str) else json.dumps(result, ensure_ascii=False)
