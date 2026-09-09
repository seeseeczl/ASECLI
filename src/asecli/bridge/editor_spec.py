"""Strict declarative contract for the narrow ASE Editor creation backend."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ._editor_primitives import ExpansionSpec, expansion_classes, primitive_class

SUPPORTED_ASE_VERSIONS = frozenset({"1.9.6.2"})
class SpecError(ValueError):
    """EditorGraphSpec is outside the explicitly supported v1 grammar."""
@dataclass(frozen=True)
class TemplateSpec:
    guid: str
    shader_name: str
    settings: dict | None = None

    def to_dict(self) -> dict:
        return ({"guid": self.guid, "shader_name": self.shader_name} if self.settings is None
                else {"guid": self.guid, "shader_name": self.shader_name, "settings": dict(self.settings)})
@dataclass(frozen=True)
class InputSpec:
    name: str
    type: str

    def to_dict(self) -> dict:
        return {"name": self.name, "type": self.type}
@dataclass(frozen=True)
class NodeSpec:
    alias: str
    kind: str
    position: tuple[float, float]
    type: str | None = None
    property_name: str | None = None
    inspector_name: str | None = None
    tooltip: str | None = None
    help: str | None = None
    enabled_if: dict | None = None
    parameter_type: str | None = None
    name: str | None = None
    code: str | None = None
    output_type: str | None = None
    inputs: tuple[InputSpec, ...] = ()
    precision: str | None = None
    default: Any | None = None
    min: float | None = None
    max: float | None = None
    op: str | None = None
    recipe: str | None = None
    expansion: ExpansionSpec | None = None
    hdr: bool | None = None
    texture_guid: str | None = None
    hidden: bool | None = None

    @property
    def ase_type(self) -> str:
        if self.kind == "sampler":
            return "SamplerNode"
        if self.kind == "custom_expression":
            return "CustomExpressionNode"
        if self.kind == "primitive":
            assert self.op is not None
            cls = primitive_class(self.op)
            assert cls is not None
            return cls
        if self.kind == "recipe":
            return "Recipe"
        assert self.type is not None
        return self.type

    def to_dict(self) -> dict:
        result: dict[str, Any] = {
            "alias": self.alias,
            "kind": self.kind,
            "position": list(self.position),
        }
        if self.type is not None:
            result["type"] = self.type
        if self.hdr is not None:
            result["hdr"] = self.hdr
        if self.hidden is not None:
            result["hidden"] = self.hidden
        if self.texture_guid is not None:
            result["texture_guid"] = self.texture_guid
        if self.precision is not None:
            result["precision"] = self.precision
        if self.default is not None:
            result["default"] = self.default
        if self.min is not None:
            result["min"] = self.min
            result["max"] = self.max
        if self.property_name is not None:
            result.update(
                property_name=self.property_name,
                inspector_name=self.inspector_name,
                parameter_type=self.parameter_type,
            )
            if self.tooltip is not None:
                result["tooltip"] = self.tooltip
            if self.help is not None:
                result["help"] = self.help
            if self.enabled_if is not None:
                result["enabled_if"] = dict(self.enabled_if)
        if self.kind == "custom_expression":
            result.update(
                name=self.name,
                code=self.code,
                output_type=self.output_type,
                inputs=[item.to_dict() for item in self.inputs],
            )
        if self.kind == "primitive":
            result["op"] = self.op
        if self.kind == "recipe":
            result.update(
                recipe=self.recipe,
                code=self.code,
                output_type=self.output_type,
                inputs=[item.to_dict() for item in self.inputs],
                expansion=self.expansion.to_dict(),
            )
        return result

    def manifest_entry(self) -> dict:
        result: dict[str, Any] = {"alias": self.alias, "kind": self.kind, "type": self.ase_type}
        if self.property_name is not None:
            result.update(
                property_name=self.property_name,
                inspector_name=self.inspector_name,
                parameter_type=self.parameter_type,
            )
        if self.hdr is not None:
            result["hdr"] = self.hdr
        if self.hidden is not None:
            result["hidden"] = self.hidden
        if self.texture_guid is not None:
            result["texture_guid"] = self.texture_guid
        if self.precision is not None:
            result["precision"] = self.precision
        if self.default is not None:
            result["default"] = self.default
        if self.min is not None:
            result["min"] = self.min
            result["max"] = self.max
        if self.kind == "custom_expression":
            result.update(
                name=self.name,
                code=self.code,
                output_type=self.output_type,
                inputs=[item.to_dict() for item in self.inputs],
            )
        if self.kind == "primitive":
            result["op"] = self.op
        if self.kind == "recipe":
            if self.expansion_is_native():
                classes = expansion_classes(self.expansion.primitives)
                assert classes is not None
                result.update(
                    recipe=self.recipe,
                    output_type=self.output_type,
                    expansion_nodes=[
                        {"id": primitive.id, "type": cls}
                        for primitive, cls in zip(self.expansion.primitives, classes)
                    ],
                )
            else:
                # Fallback: the executor emits a single CustomExpressionNode
                # using the authoritative HLSL code.
                result["type"] = "CustomExpressionNode"
                result.update(
                    name=self.recipe,
                    code=self.code,
                    output_type=self.output_type,
                    inputs=[item.to_dict() for item in self.inputs],
                )
        return result

    def expansion_is_native(self) -> bool:
        assert self.expansion is not None
        if expansion_classes(self.expansion.primitives) is None:
            return False
        ids = {primitive.id for primitive in self.expansion.primitives}
        return self.expansion.output in ids
@dataclass(frozen=True)
class EndpointSpec:
    node: str
    port: int

    def to_dict(self) -> dict:
        return {"node": self.node, "port": self.port}
@dataclass(frozen=True)
class ConnectionSpec:
    source: EndpointSpec
    destination: EndpointSpec

    def to_dict(self) -> dict:
        return {"from": self.source.to_dict(), "to": self.destination.to_dict()}
@dataclass(frozen=True)
class EditorGraphSpec:
    version: int
    template: TemplateSpec
    nodes: tuple[NodeSpec, ...]
    connections: tuple[ConnectionSpec, ...]
    primitives_version: int | None = None

    @classmethod
    def from_dict(cls, value: Any) -> "EditorGraphSpec":
        from ._editor_spec_validation import parse_editor_graph_spec

        return parse_editor_graph_spec(value)

    def to_dict(self) -> dict:
        result: dict[str, Any] = {
            "version": self.version,
            "template": self.template.to_dict(),
            "nodes": [node.to_dict() for node in self.nodes],
            "connections": [item.to_dict() for item in self.connections],
        }
        if self.primitives_version is not None:
            result["primitives_version"] = self.primitives_version
        return result

    def editor_payload(self, asset_path: str, temporary_asset_path: str) -> dict:
        payload = self.to_dict()
        payload["version"] = 1
        for node in payload["nodes"]:
            node.pop("help", None)
            node.pop("tooltip", None)
            node.pop("enabled_if", None)
        return {**payload, "asset_path": asset_path, "temporary_asset_path": temporary_asset_path}

    def expected_manifest(self) -> dict:
        return {
            "template": self.template.to_dict(),
            "nodes": [node.manifest_entry() for node in self.nodes],
            "connections": [item.to_dict() for item in self.connections],
        }
def load_editor_graph_spec(path: str | Path) -> EditorGraphSpec:
    from ._editor_spec_io import load_editor_graph_spec as _load

    return _load(path)


def route_create_backend(requested: str, spec: EditorGraphSpec | None) -> str:
    from ._editor_spec_io import route_create_backend as _route

    return _route(requested, spec)
