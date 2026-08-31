"""Core ASE graph data model (TASK-0003/TASK-0004)."""

from __future__ import annotations

from dataclasses import dataclass, field


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

    def node_by_id(self, node_id: str) -> NodeLine | None:
        for kind, raw in self.instructions:
            if kind == "node":
                n = _parse_node_line(raw)
                if n.node_id == node_id:
                    return n
        return None

    @property
    def nodes(self) -> list[NodeLine]:
        return [_parse_node_line(raw) for kind, raw in self.instructions if kind == "node"]

    @property
    def wires(self) -> list[WireLine]:
        return [_parse_wire_line(raw) for kind, raw in self.instructions if kind == "wire"]

    def replace_node(self, node: NodeLine) -> None:
        for i, (kind, raw) in enumerate(self.instructions):
            if kind == "node" and _parse_node_line(raw).node_id == node.node_id:
                self.instructions[i] = ("node", node.to_line())
                return
        raise KeyError(f"node id {node.node_id} not found")

    def add_node(self, node: NodeLine) -> None:
        self.instructions.append(("node", node.to_line()))

    def add_wire(self, wire: WireLine) -> None:
        self.instructions.append(("wire", wire.to_line()))

    def remove_wire(self, out_node: str, out_port: str, in_node: str, in_port: str) -> bool:
        target = (out_node, out_port, in_node, in_port)
        for i, (kind, raw) in enumerate(self.instructions):
            if kind == "wire":
                w = _parse_wire_line(raw)
                if (w.out_node, w.out_port, w.in_node, w.in_port) == target:
                    del self.instructions[i]
                    return True
        return False

    def serialize(self) -> str:
        parts = [f"Version={self.version}" if not self.version.startswith("Version=") else self.version]
        for _, raw in self.instructions:
            parts.append(raw)
        return "\n".join(parts) + "\n"


def parse_graph_text(body: str) -> AseGraph:
    """Parse the text between ``/*ASEBEGIN`` and ``ASEEND*/``.

    The body excludes the markers themselves; first line is ``Version=..``.
    Raises ``ValueError`` on structural violations.
    """
    graph = AseGraph()
    lines = body.splitlines()
    if not lines:
        raise ValueError("empty ASE graph body")
    if not lines[0].startswith("Version="):
        raise ValueError(f"first graph line must be Version=..., got: {lines[0]!r}")
    graph.version = lines[0].removeprefix("Version=")
    for line in lines[1:]:
        line = line.rstrip("\r")
        if not line:
            continue
        if line.startswith("Node;"):
            _parse_node_line(line)
            graph.instructions.append(("node", line))
        elif line.startswith("WireConnection;"):
            _parse_wire_line(line)
            graph.instructions.append(("wire", line))
        else:
            graph.instructions.append(("other", line))
    return graph


def _parse_node_line(line: str) -> NodeLine:
    fields = line.split(";")
    if len(fields) < 4:
        raise ValueError(f"malformed Node line: {line!r}")
    return NodeLine(type_name=fields[1], node_id=fields[2], raw_fields=fields)


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
        if text[body_start] == "\n":
            body_start += 1
            prefix += "\n"
        body = text[body_start:end]
        suffix = text[end:]
        graph = parse_graph_text(body)
        return cls(prefix=prefix, body=body, suffix=suffix, graph=graph)

    @classmethod
    def from_path(cls, path: str | __import__("pathlib").Path) -> "AseFile":
        from pathlib import Path as _P

        return cls.from_text(_P(path).read_text(encoding="utf-8"))

    def serialize(self) -> str:
        """Rebuild full text; without mutations this is byte-identical to source."""
        return self.prefix + self.graph.serialize() + self.suffix
