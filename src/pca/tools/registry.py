"""Tool registry: the only place a tool name becomes a callable."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ValidationError

from pca.core.errors import SchemaRejected
from pca.core.types import ActionProposal, ToolSpec
from pca.tools.base import Tool


def _spec_for(tool: Tool) -> ToolSpec:
    schema: dict[str, Any] = tool.Input.model_json_schema()
    properties = list(schema.get("properties", {}))
    required = list(schema.get("required", []))
    summary = (tool.__doc__ or tool.name).strip().splitlines()[0]
    return ToolSpec(
        name=tool.name,
        version=tool.version,
        summary=summary,
        required=required,
        optional=[p for p in properties if p not in required],
    )


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        if tool.name in self._tools:
            raise ValueError(f"tool already registered: {tool.name}")
        self._tools[tool.name] = tool

    def names(self) -> list[str]:
        return sorted(self._tools)

    def specs(self) -> list[ToolSpec]:
        """Describe every tool for the planner: names plus argument shapes.

        The planner was previously given bare names, so it had to guess that
        filesystem.move takes source and destination. A real model run produced
        invalid arguments in 6 of 15 tasks.
        """
        return [_spec_for(self._tools[name]) for name in self.names()]

    def get(self, name: str) -> Tool:
        try:
            return self._tools[name]
        except KeyError:
            raise SchemaRejected(f"unknown tool: {name}") from None

    def resolve(self, proposal: ActionProposal) -> tuple[Tool, BaseModel]:
        """Turn an untrusted proposal into a validated (tool, args) pair."""
        tool = self.get(proposal.tool)
        try:
            args = tool.Input.model_validate(proposal.arguments)
        except ValidationError as exc:
            raise SchemaRejected(
                f"invalid arguments for {proposal.tool}: {exc.error_count()} problem(s)"
            ) from exc
        return tool, args
