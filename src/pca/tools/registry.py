"""Tool registry: the only place a tool name becomes a callable."""

from __future__ import annotations

from pydantic import BaseModel, ValidationError

from pca.core.errors import SchemaRejected
from pca.core.types import ActionProposal
from pca.tools.base import Tool


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        if tool.name in self._tools:
            raise ValueError(f"tool already registered: {tool.name}")
        self._tools[tool.name] = tool

    def names(self) -> list[str]:
        return sorted(self._tools)

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
