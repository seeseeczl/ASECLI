"""Native ASE CommentaryNode inspection and semantic grouping."""

from __future__ import annotations

from .graph_ops import next_free_node_id
from .model import AseGraph, NodeLine


COMMENTARY_TYPE = "AmplifyShaderEditor.CommentaryNode"
DEFAULT_NODE_WIDTH = 200.0
DEFAULT_NODE_HEIGHT = 120.0
NodeBounds = tuple[float, float, float, float]


def parse_commentary_node(node: NodeLine) -> dict:
    """Decode the variable-length ASE 1.9.6.2 CommentaryNode payload."""
    if node.type_name != COMMENTARY_TYPE:
        raise ValueError(f"node {node.node_id} is not a CommentaryNode")
    fields = node.raw_fields
    if len(fields) < 14:
        raise ValueError(f"CommentaryNode {node.node_id} has too few serialized fields")
    try:
        width = float(fields[6])
        height = float(fields[7])
        count = int(fields[9])
    except ValueError as exc:
        raise ValueError(f"CommentaryNode {node.node_id} has invalid size or member count") from exc
    if count < 0 or len(fields) != 14 + count:
        raise ValueError(f"CommentaryNode {node.node_id} member count does not match its payload")
    members = fields[10 : 10 + count]
    if len(set(members)) != len(members):
        raise ValueError(f"CommentaryNode {node.node_id} contains duplicate member ids")
    x, y = _position(node)
    if width <= 0 or height <= 0:
        raise ValueError(f"CommentaryNode {node.node_id} must have positive width and height")
    return {
        "node_id": node.node_id,
        "position": {"x": x, "y": y},
        "width": width,
        "height": height,
        "note": fields[8],
        "members": members,
        "title": fields[10 + count],
        "color": fields[11 + count],
    }


def inspect_comment_groups(graph: AseGraph) -> list[dict]:
    return [parse_commentary_node(node) for node in graph.nodes if node.type_name == COMMENTARY_TYPE]


def create_comment_group(
    graph: AseGraph,
    member_ids: list[str],
    title: str,
    *,
    note: str = "Comment",
    padding: float = 50.0,
    node_id: int | None = None,
    node_bounds: dict[str, NodeBounds] | None = None,
) -> dict:
    """Create one native Comment frame around nodes without moving them or their wires."""
    _require_supported_graph(graph)
    _validate_text(title, "title", allow_empty=False)
    _validate_text(note, "note", allow_empty=True)
    if not member_ids:
        raise ValueError("a comment group requires at least one member node")
    normalized = [str(value) for value in member_ids]
    if len(set(normalized)) != len(normalized):
        raise ValueError("comment group member ids must be unique")
    if not 0 <= padding <= 1000:
        raise ValueError("padding must be between 0 and 1000")

    members: list[NodeLine] = []
    for member_id in normalized:
        member = graph.node_by_id(member_id)
        if member is None:
            raise KeyError(f"node {member_id} not found")
        members.append(member)

    new_id = next_free_node_id(graph) if node_id is None else node_id
    if new_id < 0 or graph.node_by_id(str(new_id)) is not None:
        raise ValueError(f"comment node id {new_id} is invalid or already exists")
    if str(new_id) in normalized:
        raise ValueError("a comment group cannot contain itself")
    _validate_membership(graph, normalized)

    bounds = [_node_bounds(node, node_bounds) for node in members]
    min_x = min(item[0] for item in bounds)
    min_y = min(item[1] for item in bounds)
    max_x = max(item[2] for item in bounds)
    max_y = max(item[3] for item in bounds)
    x = min_x - padding
    y = min_y - padding
    width = max(100.0, max_x - min_x + 2 * padding)
    height = max(100.0, max_y - min_y + 2 * padding)
    fields = [
        "Node", COMMENTARY_TYPE, str(new_id), f"{_number(x)},{_number(y)}", "Inherit", "False",
        _number(width), _number(height), note, str(len(normalized)), *normalized,
        title, "1,1,1,1", "0", "0",
    ]
    node = NodeLine(type_name=COMMENTARY_TYPE, node_id=str(new_id), raw_fields=fields)
    _validate_new_group_overlap(graph, node, normalized)
    graph.add_node(node)
    return parse_commentary_node(node)


def _validate_membership(graph: AseGraph, member_ids: list[str]) -> None:
    groups = inspect_comment_groups(graph)
    parent_of: dict[str, str] = {}
    children: dict[str, list[str]] = {}
    for group in groups:
        children[group["node_id"]] = group["members"]
        for member_id in group["members"]:
            if member_id in parent_of:
                raise ValueError(f"node {member_id} already belongs to multiple comment groups")
            parent_of[member_id] = group["node_id"]
    selected = set(member_ids)
    for member_id in member_ids:
        stack = list(children.get(member_id, []))
        visited: set[str] = set()
        while stack:
            descendant = stack.pop()
            if descendant in visited:
                raise ValueError("existing comment groups contain a membership cycle")
            visited.add(descendant)
            if descendant in selected:
                raise ValueError("select a nested comment frame or its children, not both")
            stack.extend(children.get(descendant, []))
    for member_id in member_ids:
        if member_id in parent_of:
            raise ValueError(f"node {member_id} already belongs to comment group {parent_of[member_id]}")


def _node_bounds(
    node: NodeLine,
    measured: dict[str, NodeBounds] | None = None,
) -> NodeBounds:
    if measured is not None and node.node_id in measured and node.type_name != COMMENTARY_TYPE:
        x, y, width, height = measured[node.node_id]
        if width < 0 or height < 0:
            raise ValueError(f"node {node.node_id} has invalid measured bounds")
        return x, y, x + width, y + height
    x, y = _position(node)
    if node.type_name == COMMENTARY_TYPE:
        group = parse_commentary_node(node)
        width, height = group["width"], group["height"]
    else:
        width, height = DEFAULT_NODE_WIDTH, DEFAULT_NODE_HEIGHT
    return x, y, x + width, y + height


def _rect_overlap(
    left: NodeBounds,
    right: NodeBounds,
    *,
    tolerance: float = 0.01,
) -> dict[str, float] | None:
    overlap_left = max(left[0], right[0])
    overlap_top = max(left[1], right[1])
    width = min(left[2], right[2]) - overlap_left
    height = min(left[3], right[3]) - overlap_top
    if width <= tolerance or height <= tolerance:
        return None
    return {
        "x": round(overlap_left, 3),
        "y": round(overlap_top, 3),
        "width": round(width, 3),
        "height": round(height, 3),
    }


def _validate_new_group_overlap(graph: AseGraph, candidate: NodeLine, member_ids: list[str]) -> None:
    """Reject partial/sibling overlap while allowing explicit full-containment nesting."""
    groups = {group["node_id"]: group for group in inspect_comment_groups(graph)}
    allowed_nested: set[str] = set()
    stack = [member_id for member_id in member_ids if member_id in groups]
    while stack:
        group_id = stack.pop()
        if group_id in allowed_nested:
            continue
        allowed_nested.add(group_id)
        stack.extend(member_id for member_id in groups[group_id]["members"] if member_id in groups)

    candidate_bounds = _node_bounds(candidate)
    for group_id in sorted(groups, key=lambda value: (0, int(value)) if value.lstrip("-").isdigit() else (1, value)):
        if group_id in allowed_nested:
            continue
        existing = graph.node_by_id(group_id)
        assert existing is not None
        overlap = _rect_overlap(candidate_bounds, _node_bounds(existing))
        if overlap is not None:
            raise ValueError(f"comment group would overlap unrelated comment group {group_id}")


def _position(node: NodeLine) -> tuple[float, float]:
    try:
        x_raw, y_raw = node.raw_fields[3].split(",")
        return float(x_raw), float(y_raw)
    except (IndexError, ValueError) as exc:
        raise ValueError(f"node {node.node_id} has invalid x,y position") from exc


def _validate_text(value: str, label: str, *, allow_empty: bool) -> None:
    if not isinstance(value, str):
        raise ValueError(f"comment {label} must be a string")
    if len(value) > 4096:
        raise ValueError(f"comment {label} must not exceed 4096 characters")
    if any(char in value for char in (";", "\r", "\n")):
        raise ValueError(f"comment {label} contains a forbidden serialization character")
    if not allow_empty and not value.strip():
        raise ValueError(f"comment {label} must not be empty")


def _require_supported_graph(graph: AseGraph) -> None:
    try:
        version = int(graph.version)
    except ValueError as exc:
        raise ValueError(f"unsupported non-numeric ASE graph version: {graph.version!r}") from exc
    if version <= 12002:
        raise ValueError(f"graph version {graph.version} predates the supported CommentaryNode format")


def _number(value: float) -> str:
    return str(int(value)) if value.is_integer() else format(value, ".6g")
