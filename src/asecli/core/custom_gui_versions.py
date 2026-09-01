"""Verified ASE graph-version capabilities for custom material GUI metadata."""

from __future__ import annotations

from .model import AseGraph


TARGET_ASE_VERSION = "1.9.6.2"
TARGET_GRAPH_VERSION = "19602"
CUSTOM_EDITOR_GRAPH_VERSIONS = frozenset(("19109", "19602"))
MZGUI_TAIL_GRAPH_VERSIONS = frozenset(("19602",))


def _require_graph_version(graph: AseGraph, supported: frozenset[str], capability: str) -> None:
    try:
        int(graph.version)
    except ValueError as exc:
        raise ValueError(f"unsupported non-numeric ASE graph version: {graph.version!r}") from exc
    if graph.version not in supported:
        versions = ", ".join(sorted(supported))
        raise ValueError(
            f"unsupported ASE graph version {graph.version!r} for {capability}; verified versions: {versions}"
        )


def require_custom_editor_version(graph: AseGraph) -> None:
    _require_graph_version(graph, CUSTOM_EDITOR_GRAPH_VERSIONS, "serialized CustomEditor")


def require_mzgui_tail_version(graph: AseGraph) -> None:
    _require_graph_version(graph, MZGUI_TAIL_GRAPH_VERSIONS, "MZGUI property metadata")
