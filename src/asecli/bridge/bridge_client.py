"""DSH-Bridge transport: drive a running editor through its file mailbox.

The bridge is a resident DSH service that drops one probe package into the
editor project; it opens no port.  Per request, under
``Library/DSHBridge/<bootId>/``:

* ``inbox/``   - we write our request here (``<id>.json``)
* ``outbox/``  - the probe writes its response here (``<id>.json``)
* ``done/``    - the probe moves the *request* here once it has been handled

So the response must be read from ``outbox/``.  Reading ``done/`` yields the
handled request itself, which looks like an answer but carries no result.

Permission note (AA-SEC-010): the only capability used is
``unity.code.execute``.  The bridge enables it by default and it is deliberately
*not* part of its dangerous-capability allow-list, because allowing arbitrary C#
makes every other allow-list entry moot.  In practice a script runs with the
editor process's own rights - it can read any file that editor can read.  Treat
this transport as equivalent to running code locally, not as a sandbox.
"""

from __future__ import annotations

import json
import os
import time
import uuid
from pathlib import Path

from .bridge_instance import BRIDGE_ROOT, instance_is_stale, read_instance
from .bridge_mailbox import GRACE_POLLS, ownership_mismatch, result_of, sweep_outbox

COMMAND_EXECUTE = "unity.code.execute"
DEFAULT_TIMEOUT = 180.0
POLL_INTERVAL = 0.05


class BridgeError(RuntimeError):
    """Raised for any DSH-Bridge transport or command failure."""

    def __init__(self, message: str, *, phase: str | None = None, data: dict | None = None):
        super().__init__(message)
        self.phase = phase
        self.data = data or {}


class BridgeClient:
    """Mailbox client mirroring :class:`CodelyClient`'s shape."""

    def __init__(self, project_root: str | Path, *, timeout: float = DEFAULT_TIMEOUT):
        self.project_root = Path(project_root).resolve()
        self.timeout = timeout
        self.instance: dict = {}
        # 超时后仍抢救到响应的次数。调用方据此知道「超时并不等于失败」。
        self.late_recovered = 0

    def connect(self) -> dict:
        instance = read_instance(self.project_root)
        if instance is None:
            raise BridgeError(
                f"no DSH-Bridge instance for {self.project_root}; "
                "install the bridge probe or open the project in the editor",
                phase="discover",
            )
        self.instance = instance
        return instance

    def _mailbox(self) -> Path:
        boot_id = self.instance["bootId"]
        return self.project_root / BRIDGE_ROOT / boot_id

    @staticmethod
    def _backlog(inbox: Path, exclude: str) -> list[str]:
        """Requests already queued ahead of ours.

        The probe handles one file per tick in ordinal order, so a stuck or
        malformed entry delays everything behind it.  Counting the backlog lets
        a timeout explain *why* it happened instead of looking like a hang.
        """
        try:
            return [i.name for i in sorted(inbox.glob("*.json")) if i.name != f"{exclude}.json"]
        except OSError:
            return []

    def execute_code(self, code: str) -> str:
        """Run *code* through ``unity.code.execute`` and return its result text.

        The bridge answers with a JSON object; callers expect the payload the
        script produced, so the result is re-serialised as JSON text.
        """
        if not self.instance:
            self.connect()
        request_id = f"req_asecli_{uuid.uuid4().hex[:16]}"
        mailbox = self._mailbox()
        inbox = mailbox / "inbox"
        outbox = mailbox / "outbox"
        if not inbox.is_dir():
            raise BridgeError(f"bridge mailbox missing: {inbox}", phase="discover")
        # Drop leftovers from an earlier crash of ours so they cannot block the
        # queue ahead of this request (AA-OPT-011).
        for stale in inbox.glob(".req_asecli_*.tmp"):
            try:
                stale.unlink()
            except OSError:
                pass
        sweep_outbox(outbox)
        backlog = self._backlog(inbox, request_id)
        payload = {
            "v": 1,
            "id": request_id,
            "instanceId": self.instance["instanceId"],
            "bootId": self.instance["bootId"],
            "nonce": self.instance["nonce"],
            "cap": COMMAND_EXECUTE,
            "args": {"code": code},
            "issuedAt": int(time.time() * 1000),
            "deadlineMs": int(self.timeout * 1000),
        }
        tmp = inbox / f".{request_id}.tmp"
        target = inbox / f"{request_id}.json"
        try:
            tmp.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
            os.replace(tmp, target)
        except OSError as exc:
            raise BridgeError(f"cannot deliver bridge request: {exc}", phase="write") from exc
        try:
            expect = {"id": request_id, "instanceId": self.instance["instanceId"],
                      "bootId": self.instance["bootId"], "nonce": self.instance["nonce"]}
            return self._await(request_id, outbox, backlog, expect)
        finally:
            for path in (target, outbox / f"{request_id}.json"):
                try:
                    path.unlink()
                except OSError:
                    pass

    def _await(self, request_id: str, outbox: Path, backlog: list[str],
               expect: dict | None = None) -> str:
        """Poll ``outbox/`` until a response belonging to this request arrives.

        The probe validates our request; we must equally validate its answer.
        A stale or planted file with a matching name would otherwise be read as
        this call's result (AA-SEC-020).
        """
        deadline = time.monotonic() + self.timeout
        while time.monotonic() < deadline:
            response = self._read_response(request_id, outbox)
            if response is None:
                time.sleep(POLL_INTERVAL)
                continue
            return self._accept(response, request_id, expect)
        # 主超时到了，但结论还没定：探针可能刚写完响应，或者已经写了却刚好错过
        # 最后一次轮询。补读一次——拿到就按正常路径处理，避免「其实成功」被报成超时。
        late = self._read_response(request_id, outbox)
        if late is not None:
            self.late_recovered += 1
            return self._accept(late, request_id, expect)
        # Work we already triggered may answer marginally late; adopt it
        # instead of reporting a bare failure.
        for _ in range(GRACE_POLLS):
            time.sleep(POLL_INTERVAL)
            late = self._read_response(request_id, outbox)
            if late is not None and not ownership_mismatch(late, expect or {}):
                return result_of(late, BridgeError)
        hint = (
            f"; {len(backlog)} request(s) were already queued ahead, so the "
            "mailbox may be blocked by a malformed entry"
            if backlog
            else ""
        )
        raise BridgeError(
            f"bridge {COMMAND_EXECUTE} timed out after {self.timeout:.0f}s{hint}; "
            "the request was delivered, so the script may already have run - "
            "check the target state before retrying",
            phase="timeout",
            data={
                "request_id": request_id,
                "delivery": "delivered",
                "inbox_backlog": len(backlog),
                # 没读到任何响应：无法判断脚本执行到哪一步。显式标成 unknown，
                # 而不是让调用方猜——与探针侧的 executionState 语义保持一致。
                "execution_state": "unknown",
                "evidence": "no-response",
            },
        )

    def _accept(self, response: dict, request_id: str, expect: dict | None) -> str:
        """Validate one response and turn it into the caller-visible result."""
        mismatch = ownership_mismatch(response, expect or {})
        if mismatch:
            # A file with our id but another owner's fields can only be a
            # leftover or a plant; the real answer never becomes valid later,
            # so fail now instead of burning the whole timeout.
            raise BridgeError(
                f"bridge response for {request_id} does not belong to this call "
                f"({mismatch}); refusing to accept it",
                phase="protocol",
                data={"request_id": request_id, "mismatch": mismatch},
            )
        if not response.get("ok"):
            error = response.get("error") or {}
            code = error.get("code") if isinstance(error, dict) else None
            message = error.get("message") if isinstance(error, dict) else None
            headline = (message or code or "unknown error").splitlines()[0]
            raise BridgeError(
                f"bridge {COMMAND_EXECUTE} failed: {headline}"
                + (f" (code={code})" if code else ""),
                phase="command",
                data=dict(error, detail=message) if isinstance(error, dict) else {"detail": message},
            )
        return result_of(response, BridgeError)

    @staticmethod
    def _read_response(request_id: str, outbox: Path) -> dict | None:
        """Read the answer from ``outbox/``.

        The probe writes its response to ``outbox/`` and moves the *request* into
        ``done/``, so reading ``done/`` would mistake the request echo for an
        answer; ``inbox/`` still holds our own request until it is collected.
        """
        candidate = outbox / f"{request_id}.json"
        try:
            if not candidate.is_file():
                return None
            data = json.loads(candidate.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None
        # A response always reports `ok`; anything else is a stray file.
        return data if isinstance(data, dict) and "ok" in data else None

    def close(self) -> None:
        self.instance = {}

    def __enter__(self) -> "BridgeClient":
        self.connect(); return self

    def __exit__(self, *exc_info) -> None:
        self.close()
