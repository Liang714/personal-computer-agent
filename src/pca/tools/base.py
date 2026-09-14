"""The typed tool contract (spec §11)."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import ClassVar

from pydantic import BaseModel

from pca.core.types import Capability, RiskLevel, ToolResult
from pca.policy.paths import Workspace


class Tool(ABC):
    """Every capability the agent has. Declares its own permission and base risk."""

    name: ClassVar[str]
    version: ClassVar[str]
    capability: ClassVar[Capability]
    base_risk: ClassVar[RiskLevel]
    Input: ClassVar[type[BaseModel]]
    Output: ClassVar[type[BaseModel]]

    @abstractmethod
    def run(self, args: BaseModel, workspace: Workspace) -> ToolResult:
        """Execute. Never called except by the broker."""
