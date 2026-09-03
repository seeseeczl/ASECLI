"""Deterministically compose packaged text resources from ordered fragments."""

from __future__ import annotations

from importlib import resources
from typing import Iterable


def compose_resource_text(package: str, directory: str, fragments: Iterable[str]) -> str:
    """Return the byte-stable UTF-8 concatenation of explicitly ordered fragments."""
    root = resources.files(package).joinpath(directory)
    return "".join(root.joinpath(name).read_text(encoding="utf-8") for name in fragments)
