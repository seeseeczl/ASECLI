"""ASE checksum: SHA1 (uppercase hex) of the full text before ``//CHKSM=``.

Replicates ``IOUtils.CreateChecksum``; verified against real files.
"""

from __future__ import annotations

import hashlib
import re

MARKER = "//CHKSM="
_TRAILER = re.compile(r"(?m)^//CHKSM=([^\r\n]*)(\r?\n)?\Z")
_LINE_MARKER = re.compile(r"(?m)^//CHKSM=")


class ChecksumFormatError(ValueError):
    """Raised when checksum-like lines are ambiguous or not a trailer."""


def compute_checksum(text_before: str) -> str:
    return hashlib.sha1(text_before.encode("utf-8")).hexdigest().upper()


def verify_checksum(text: str) -> tuple[bool, str | None, str | None]:
    match = _checksum_trailer(text)
    if match is None:
        return False, None, None
    idx = match.start()
    stored = match.group(1).strip()
    actual = compute_checksum(text[:idx])
    return bool(re.fullmatch(r"[0-9A-Fa-f]{40}", stored)) and stored.upper() == actual, stored, actual


def fix_checksum(text: str) -> str:
    match = _checksum_trailer(text)
    if match is None:
        sep = "" if text.endswith("\n") else "\n"
        return text + sep + MARKER + compute_checksum(text)
    idx = match.start()
    trailing_eol = match.group(2) or ""
    return text[:idx] + MARKER + compute_checksum(text[:idx]) + trailing_eol


def _checksum_trailer(text: str) -> re.Match[str] | None:
    markers = list(_LINE_MARKER.finditer(text))
    match = _TRAILER.search(text)
    if match is None:
        if markers:
            raise ChecksumFormatError("//CHKSM= must be the final standalone line")
        return None
    if len(markers) != 1 or markers[0].start() != match.start():
        raise ChecksumFormatError("multiple //CHKSM= lines are ambiguous")
    return match
