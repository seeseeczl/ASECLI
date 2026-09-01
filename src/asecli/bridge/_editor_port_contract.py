"""ASE 1.9.6.2 port contracts exposed by EditorGraphSpec v1."""

from __future__ import annotations

from .editor_spec import ConnectionSpec, NodeSpec, SpecError, TemplateSpec


_NUMERIC_TYPES = frozenset({"INT", "FLOAT", "FLOAT2", "FLOAT3", "FLOAT4", "COLOR"})
_MATRIX_TYPES = frozenset({"FLOAT3x3", "FLOAT4x4"})
_DYNAMIC_NUMERIC = "DYNAMIC_NUMERIC"
_URP_UNLIT_GUID = "2992e84f91cbeb14eab234972e07ea9d"
_URP_UNLIT_MASTER_INPUTS = {
    0: "FLOAT3",  # Baked Albedo
    1: "FLOAT3",  # Baked Emission
    2: "FLOAT3",  # Color
    3: "FLOAT",   # Alpha
    4: "FLOAT",   # Alpha Clip Threshold
    5: "FLOAT3",  # Vertex Offset / Position
    6: "FLOAT3",  # Vertex Normal
    7: "FLOAT",   # Alpha Clip Threshold Shadow
}
_STATIC_INPUT_PORTS = {
    "WorldPosInputsNode": {},
    "TextureCoordinatesNode": {0: "FLOAT2", 1: "FLOAT2", 2: "SAMPLER2D"},
    "BreakToComponentsNode": {0: _DYNAMIC_NUMERIC},
    "TexturePropertyNode": {},
    "RangedFloatNode": {},
    "Matrix4X4Node": {},
    "Vector4Node": {},
    "SamplerNode": {
        0: "SAMPLER2D", 1: "FLOAT2", 2: "FLOAT", 3: "FLOAT2",
        4: "FLOAT2", 5: "FLOAT", 6: "FLOAT", 7: "SAMPLERSTATE",
    },
}
_STATIC_OUTPUT_PORTS = {
    "WorldPosInputsNode": {0: "FLOAT3", 1: "FLOAT", 2: "FLOAT", 3: "FLOAT"},
    "TextureCoordinatesNode": {0: "FLOAT2", 1: "FLOAT", 2: "FLOAT", 3: "FLOAT", 4: "FLOAT"},
    "BreakToComponentsNode": {port: "FLOAT" for port in range(16)},
    "TexturePropertyNode": {0: "SAMPLER2D", 1: "SAMPLERSTATE"},
    "RangedFloatNode": {0: "FLOAT"},
    "Matrix4X4Node": {0: "FLOAT4x4"},
    "Vector4Node": {0: "FLOAT4", 1: "FLOAT", 2: "FLOAT", 3: "FLOAT", 4: "FLOAT"},
    "SamplerNode": {
        0: "COLOR", 1: "FLOAT", 2: "FLOAT", 3: "FLOAT", 4: "FLOAT", 5: "FLOAT3",
    },
}


def validate_connections(
    template: TemplateSpec,
    nodes: tuple[NodeSpec, ...],
    connections: tuple[ConnectionSpec, ...],
) -> None:
    by_alias = {node.alias: node for node in nodes}
    for index, connection in enumerate(connections):
        source = by_alias[connection.source.node]
        source_type = _output_ports(source).get(connection.source.port)
        if source_type is None:
            raise SpecError(
                f"connections[{index}] source port {connection.source.port} does not exist on {source.alias}"
            )

        if connection.destination.node == "master":
            if template.guid != _URP_UNLIT_GUID:
                raise SpecError(
                    f"connections[{index}] template guid has no verified master-port contract"
                )
            destination_ports = _URP_UNLIT_MASTER_INPUTS
        else:
            destination_ports = _input_ports(by_alias[connection.destination.node])
        destination_type = destination_ports.get(connection.destination.port)
        if destination_type is None:
            raise SpecError(
                f"connections[{index}] destination port {connection.destination.port} does not exist on "
                f"{connection.destination.node}"
            )
        if not _compatible_port_types(source_type, destination_type):
            raise SpecError(
                f"connections[{index}] incompatible port types: {source_type} to {destination_type}"
            )


def _input_ports(node: NodeSpec) -> dict[int, str]:
    if node.kind == "custom_expression":
        return {index: item.type for index, item in enumerate(node.inputs)}
    return _STATIC_INPUT_PORTS[node.ase_type]


def _output_ports(node: NodeSpec) -> dict[int, str]:
    if node.kind == "custom_expression":
        assert node.output_type is not None
        return {0: node.output_type}
    return _STATIC_OUTPUT_PORTS[node.ase_type]


def _compatible_port_types(source: str, destination: str) -> bool:
    if destination == _DYNAMIC_NUMERIC:
        return source in _NUMERIC_TYPES or source in _MATRIX_TYPES
    if source in _NUMERIC_TYPES and destination in _NUMERIC_TYPES:
        return True
    return source == destination
