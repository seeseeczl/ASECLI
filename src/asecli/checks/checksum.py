"""ASE checksum: SHA1 (uppercase hex) of the full text before ``//CHKSM=``.

Replicates ``IOUtils.CreateChecksum``; verified against real files.
"""

from __future__ import annotations

import hashlib

MARKER = "//CHKSM="


def compute_checksum(text_before: str) -> str:
    return hashlib.sha1(text_before.encode("utf-8")).hexdigest().upper()


def verify_checksum(text: str) -> tuple[bool, str | None, str | None]:
    idx = text.find(MARKER)
    if idx < 0:
        return False, None, None
    stored = text[idx + len(MARKER) :].strip().split("\n", 1)[0].strip()
    actual = compute_checksum(text[:idx])
    return stored == actual, stored, actual


def fix_checksum(text: str) -> str:
    idx = text.find(MARKER)
    if idx < 0:
        sep = "" if text.endswith("\n") else "\n"
        return text + sep + MARKER + compute_checksum(text)
    return text[:idx] + MARKER + compute_checksum(text[:idx])
