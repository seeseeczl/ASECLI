"""Core ASE graph data model (TASK-0003/TASK-0004)."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from collections import Counter


@dataclass
class NodeLine:
    """A raw ``Node;`` instruction line from the ASEBEGIN block."""

    type_name: str
    node_id: str
    raw_fields: list[str]

    def to_line(self) -> str:
        return ";".join(self.raw_fields)


@dataclass
class WireLine:
    """A raw ``WireConnection;`` instruction.

    ASE format: ``WireConnection;<in_node>;<in_port>;<out_node>;<out_port>``
    (destination first, source second — verified against real files).
    """

    out_node: str
    out_port: str
    in_node: str
    in_port: str

    def to_line(self) -> str:
        return f"WireConnection;{self.in_node};{self.in_port};{self.out_node};{self.out_port}"


@dataclass
class AseGraph:
    """Parsed representation of one ASEBEGIN..ASEEND block.

    Preserves the raw instruction stream so that serialize(parse(x)) == x
    byte-for-byte, and mutations produce minimal diffs. Unrecognized lines
    (canvas params, comments, future ASE additions) are kept verbatim.
    """

    version: str = ""
    instructions: list[tuple[str, str]] = field(default_factory=list)  # (kind, raw)
    eol: str = "\n"
    version_eol: str = "\n"
    line_endings: list[str] = field(default_factory=list)

    def node_by_id(self, node_id: str) -> NodeLine | None:
        for kind, raw in self.instructions:
            if kind == "node":
                n = parse_node_line(raw)
                if n.node_id == node_id:
                    return n
        return None

    @property
    def nodes(self) -> list[NodeLine]:
        return [parse_node_line(raw) for kind, raw in self.instructions if kind == "node"]

    @property
    def wires(self) -> list[WireLine]:
        return [_parse_wire_line(raw) for kind, raw in self.instructions if kind == "wire"]

    def replace_node(self, node: NodeLine) -> None:
        for i, (kind, raw) in enumerate(self.instructions):
            if kind == "node" and parse_node_line(raw).node_id == node.node_id:
                self.instructions[i] = ("node", node.to_line())
                return
        raise KeyError(f"node id {node.node_id} not found")

    def add_node(self, node: NodeLine) -> None:
        if self.node_by_id(node.node_id) is not None:
            raise ValueError(f"node id {node.node_id} already exists")
        self._prepare_append()
        self.instructions.append(("node", node.to_line()))
        self.line_endings.append(self.eol)

    def add_wire(self, wire: WireLine) -> None:
        self._prepare_append()
        self.instructions.append(("wire", wire.to_line()))
        self.line_endings.append(self.eol)

    def remove_wire(self, out_node: str, out_port: str, in_node: str, in_port: str) -> bool:
        target = (out_node, out_port, in_node, in_port)
        for i, (kind, raw) in enumerate(self.instructions):
            if kind == "wire":
                w = _parse_wire_line(raw)
                if (w.out_node, w.out_port, w.in_node, w.in_port) == target:
                    self.delete_instruction(i)
                    return True
        return False

    def serialize(self) -> str:
        version = f"Version={self.version}" if not self.version.startswith("Version=") else self.version
        parts = [version + self.version_eol]
        for index, (_, raw) in enumerate(self.instructions):
            ending = self.line_endings[index] if index < len(self.line_endings) else self.eol
            parts.append(raw + ending)
        return "".join(parts)

    def delete_instruction(self, index: int) -> None:
        del self.instructions[index]
        if index < len(self.line_endings):
            del self.line_endings[index]

    def _prepare_append(self) -> None:
        while len(self.line_endings) < len(self.instructions):
            self.line_endings.append(self.eol)
        if self.instructions:
            if self.line_endings[len(self.instructions) - 1] == "":
                self.line_endings[len(self.instructions) - 1] = self.eol
        elif not self.instructions and self.version_eol == "":
            self.version_eol = self.eol


def parse_graph_text(body: str) -> AseGraph:
    """Parse the text between ``/*ASEBEGIN`` and ``ASEEND*/``.

    The body excludes the markers themselves; first line is ``Version=..``.
    Raises ``ValueError`` on structural violations.
    """
    graph = AseGraph()
    encoded_lines = body.splitlines(keepends=True)
    if not encoded_lines:
        raise ValueError("empty ASE graph body")
    first, graph.version_eol = _split_line_ending(encoded_lines[0])
    if not first.startswith("Version="):
        raise ValueError(f"first graph line must be Version=..., got: {first!r}")
    graph.version = first.removeprefix("Version=")
    observed_endings = [graph.version_eol] if graph.version_eol else []
    for encoded in encoded_lines[1:]:
        line, ending = _split_line_ending(encoded)
        if not line:
            graph.instructions.append(("other", ""))
        elif line.startswith("Node;"):
            parse_node_line(line)
            graph.instructions.append(("node", line))
        elif line.startswith("WireConnection;"):
            _parse_wire_line(line)
            graph.instructions.append(("wire", line))
        else:
            graph.instructions.append(("other", line))
        graph.line_endings.append(ending)
        if ending:
            observed_endings.append(ending)
    if observed_endings:
        counts = Counter(observed_endings)
        graph.eol = max(counts, key=lambda item: (counts[item], item == graph.version_eol))
    return graph


def _split_line_ending(line: str) -> tuple[str, str]:
    if line.endswith("\r\n"):
        return line[:-2], "\r\n"
    if line.endswith("\n") or line.endswith("\r"):
        return line[:-1], line[-1]
    return line, ""


def parse_node_line(line: str) -> NodeLine:
    """Parse one serialized ``Node;...`` instruction."""
    fields = line.split(";")
    if len(fields) < 4:
        raise ValueError(f"malformed Node line: {line!r}")
    return NodeLine(type_name=fields[1], node_id=fields[2], raw_fields=fields)


# Compatibility alias for callers from the pre-0.2 private API period.
_parse_node_line = parse_node_line


def _parse_wire_line(line: str) -> WireLine:
    fields = line.split(";")
    if len(fields) != 5:
        raise ValueError(f"malformed WireConnection line: {line!r}")
    return WireLine(in_node=fields[1], in_port=fields[2], out_node=fields[3], out_port=fields[4])


BEGIN = "/*ASEBEGIN"
END = "ASEEND*/"
CHECKSUM_PREFIX = "//CHKSM="


@dataclass
class AseFile:
    """A shader/function file containing exactly one ASE graph block."""

    prefix: str
    body: str  # between BEGIN (exclusive) and END (exclusive)
    suffix: str  # from END marker through checksum line(s)
    graph: AseGraph = field(default_factory=AseGraph)
    source_digest: str | None = None

    @classmethod
    def from_text(cls, text: str) -> "AseFile":
        begin = text.find(BEGIN)
        if begin < 0:
            raise ValueError("no /*ASEBEGIN marker found")
        end = text.find(END, begin)
        if end < 0:
            raise ValueError("no ASEEND*/ marker found")
        prefix = text[: begin + len(BEGIN)]
        # body starts after the newline following BEGIN, ends before END marker
        body_start = begin + len(BEGIN)
        if text[body_start : body_start + 2] == "\r\n":
            body_start += 2
            prefix += "\r\n"
        elif text[body_start] == "\n":
            body_start += 1
            prefix += "\n"
        body = text[body_start:end]
        suffix = text[end:]
        graph = parse_graph_text(body)
        return cls(prefix=prefix, body=body, suffix=suffix, graph=graph)

    @classmethod
    def from_path(cls, path: str | __import__("pathlib").Path) -> "AseFile":
        from pathlib import Path as _P

        data = _P(path).read_bytes()
        result = cls.from_text(data.decode("utf-8"))
        result.source_digest = hashlib.sha256(data).hexdigest()
        return result

    def serialize(self) -> str:
        """Rebuild full text; without mutations this is byte-identical to source."""
        return self.prefix + self.graph.serialize() + self.suffix

    def replace_graph(self, graph: AseGraph) -> None:
        """Replace only the ASE graph while preserving this file's outer shell."""
        self.graph = graph
