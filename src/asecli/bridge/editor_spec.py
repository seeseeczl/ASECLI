"""Strict declarative contract for the narrow ASE Editor creation backend."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any


SUPPORTED_ASE_VERSIONS = frozenset({"1.9.6.2"})


class SpecError(ValueError):
    """EditorGraphSpec is outside the explicitly supported v1 grammar."""


@dataclass(frozen=True)
class TemplateSpec:
    guid: str
    shader_name: str

    def to_dict(self) -> dict:
        return {"guid": self.guid, "shader_name": self.shader_name}


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

    @property
    def ase_type(self) -> str:
        if self.kind == "sampler":
            return "SamplerNode"
        if self.kind == "custom_expression":
            return "CustomExpressionNode"
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
        return result

    def manifest_entry(self) -> dict:
        result: dict[str, Any] = {"alias": self.alias, "kind": self.kind, "type": self.ase_type}
        if self.property_name is not None:
            result.update(
                property_name=self.property_name,
                inspector_name=self.inspector_name,
                parameter_type=self.parameter_type,
            )
        if self.kind == "custom_expression":
            result.update(
                name=self.name,
                code=self.code,
                output_type=self.output_type,
                inputs=[item.to_dict() for item in self.inputs],
            )
        return result


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

    @classmethod
    def from_dict(cls, value: Any) -> "EditorGraphSpec":
        from ._editor_spec_validation import parse_editor_graph_spec

        return parse_editor_graph_spec(value)

    def to_dict(self) -> dict:
        return {
            "version": self.version,
            "template": self.template.to_dict(),
            "nodes": [node.to_dict() for node in self.nodes],
            "connections": [item.to_dict() for item in self.connections],
        }

    def editor_payload(self, asset_path: str, temporary_asset_path: str) -> dict:
        # The fixed ASE executor protocol remains v1. Presentation-only fields
        # are finalized and verified by the CLI after ASE commits the graph.
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
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise SpecError(f"cannot read EditorGraphSpec JSON: {exc}") from exc
    return EditorGraphSpec.from_dict(value)


def route_create_backend(requested: str, spec: EditorGraphSpec | None) -> str:
    if requested not in {"text", "editor", "auto"}:
        raise SpecError(f"unknown create backend: {requested}")
    if requested == "auto":
        return "editor" if spec is not None else "text"
    return requested
