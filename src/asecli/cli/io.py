"""Filesystem commit helpers for CLI write commands."""

from __future__ import annotations

from contextlib import contextmanager
import hashlib
import os
from pathlib import Path
import stat
import tempfile


_UNCHECKED = object()


class UnsafeWritePathError(OSError):
    """Raised when a target, backup, or lock path is not safe to write."""


class WriteConflictError(OSError):
    """Raised when the on-disk file changed after the command loaded it."""

    def __init__(self, path: Path, expected: str | None, actual: str | None):
        super().__init__(f"file changed since load: {path}")
        self.path = path
        self.expected = expected
        self.actual = actual


def read_text_snapshot(path: str | Path) -> tuple[str, str]:
    """Read one regular UTF-8 file without following a final symlink."""
    target = Path(path)
    data, _ = _read_regular_file(target)
    return data.decode("utf-8"), _digest(data)


def file_digest(path: str | Path) -> str:
    """Return a SHA-256 snapshot without decoding the file."""
    data, _ = _read_regular_file(Path(path))
    return _digest(data)


def atomic_write(
    path: str | Path,
    text: str,
    *,
    expected_digest: str | None | object = _UNCHECKED,
) -> None:
    """Safely replace a file, back it up, and reject stale snapshots.

    ``expected_digest`` is the SHA-256 captured when the caller loaded the
    file. Passing ``None`` means the target is expected not to exist. Omitting
    it keeps the low-level helper backward compatible but disables conflict
    detection; CLI mutation paths always pass an expectation.
    """
    target = Path(path)
    if not target.parent.is_dir():
        raise FileNotFoundError(f"parent directory not found: {target.parent}")
    with _exclusive_lock(target):
        _reject_symlink(target.with_suffix(target.suffix + ".tmp"), "legacy temporary")
        current, current_mode = _current_bytes(target)
        actual_digest = _digest(current) if current is not None else None
        if expected_digest is not _UNCHECKED and actual_digest != expected_digest:
            raise WriteConflictError(target, expected_digest, actual_digest)

        if current is not None:
            backup = target.with_suffix(target.suffix + ".bak")
            _reject_symlink(backup, "backup")
            _replace_bytes(backup, current, current_mode)

        mode = current_mode if current_mode is not None else 0o644
        _replace_bytes(target, text.encode("utf-8"), mode)
        _fsync_directory(target.parent)


def _digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _current_bytes(path: Path) -> tuple[bytes | None, int | None]:
    try:
        return _read_regular_file(path)
    except FileNotFoundError:
        return None, None


def _read_regular_file(path: Path) -> tuple[bytes, int]:
    flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    try:
        fd = os.open(path, flags)
    except OSError as exc:
        if path.is_symlink():
            raise UnsafeWritePathError(f"refusing symlink path: {path}") from exc
        raise
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode):
            raise UnsafeWritePathError(f"refusing non-regular file: {path}")
        chunks = []
        while True:
            chunk = os.read(fd, 1024 * 1024)
            if not chunk:
                break
            chunks.append(chunk)
        return b"".join(chunks), stat.S_IMODE(info.st_mode)
    finally:
        os.close(fd)


def _reject_symlink(path: Path, label: str) -> None:
    try:
        info = path.lstat()
    except FileNotFoundError:
        return
    if stat.S_ISLNK(info.st_mode):
        raise UnsafeWritePathError(f"refusing {label} symlink: {path}")
    if not stat.S_ISREG(info.st_mode):
        raise UnsafeWritePathError(f"refusing non-regular {label} path: {path}")


def _replace_bytes(path: Path, data: bytes, mode: int) -> None:
    fd, raw_tmp = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    tmp = Path(raw_tmp)
    try:
        os.fchmod(fd, mode)
        with os.fdopen(fd, "wb", closefd=True) as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp, path)
    except BaseException:
        try:
            os.close(fd)
        except OSError:
            pass
        try:
            tmp.unlink()
        except FileNotFoundError:
            pass
        raise


@contextmanager
def _exclusive_lock(target: Path):
    lock = _lock_path(target)
    _reject_symlink(lock, "lock")
    flags = os.O_RDWR | os.O_CREAT | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    fd = os.open(lock, flags, 0o600)
    try:
        if os.name == "nt":  # pragma: no cover - exercised on Windows CI
            import msvcrt

            if os.fstat(fd).st_size == 0:
                os.write(fd, b"\0")
            os.lseek(fd, 0, os.SEEK_SET)
            msvcrt.locking(fd, msvcrt.LK_LOCK, 1)
        else:
            import fcntl

            fcntl.flock(fd, fcntl.LOCK_EX)
        yield
    finally:
        if os.name == "nt":  # pragma: no cover - exercised on Windows CI
            import msvcrt

            os.lseek(fd, 0, os.SEEK_SET)
            msvcrt.locking(fd, msvcrt.LK_UNLCK, 1)
        else:
            import fcntl

            fcntl.flock(fd, fcntl.LOCK_UN)
        os.close(fd)


def _lock_path(target: Path) -> Path:
    uid = getattr(os, "getuid", lambda: 0)()
    root = Path(tempfile.gettempdir()) / f"asecli-locks-{uid}"
    try:
        root.mkdir(mode=0o700)
    except FileExistsError:
        pass
    info = root.lstat()
    if stat.S_ISLNK(info.st_mode) or not stat.S_ISDIR(info.st_mode):
        raise UnsafeWritePathError(f"refusing unsafe lock directory: {root}")
    if hasattr(os, "getuid") and info.st_uid != os.getuid():
        raise UnsafeWritePathError(f"lock directory is owned by another user: {root}")
    key = hashlib.sha256(os.fsencode(str(target.resolve(strict=False)))).hexdigest()
    return root / f"{key}.lock"


def _fsync_directory(directory: Path) -> None:
    flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0)
    try:
        fd = os.open(directory, flags)
    except OSError:  # pragma: no cover - some platforms cannot open directories
        return
    try:
        os.fsync(fd)
    finally:
        os.close(fd)
