"""Core domain models (spec §4, §46)."""

from __future__ import annotations

from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from pca.core.provenance import Trust

_FROZEN = ConfigDict(extra="forbid", frozen=True)


class RiskLevel(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

    @property
    def rank(self) -> int:
        return _RISK_ORDER.index(self)


_RISK_ORDER = [RiskLevel.LOW, RiskLevel.MEDIUM, RiskLevel.HIGH, RiskLevel.CRITICAL]


class Permission(StrEnum):
    DENIED = "denied"
    ASK = "ask"
    ALLOWED = "allowed"


class Capability(StrEnum):
    FILESYSTEM_READ = "filesystem_read"
    FILESYSTEM_WRITE = "filesystem_write"
    FILESYSTEM_DELETE = "filesystem_delete"


class ActionProposal(BaseModel):
    """The ONLY thing a planner may emit. Carries no callables and no risk."""

    model_config = _FROZEN

    intent: str
    tool: str
    arguments: dict[str, Any] = Field(default_factory=dict)
    expected: dict[str, Any] = Field(default_factory=dict)


class ToolResult(BaseModel):
    model_config = _FROZEN

    ok: bool
    data: dict[str, Any] = Field(default_factory=dict)
    trust: Trust = Trust.TOOL_OUTPUT


class VerificationResult(BaseModel):
    model_config = _FROZEN

    status: Literal["success", "failed", "ambiguous"]
    detail: str = ""


class ToolSpec(BaseModel):
    """What the planner is told about a tool: a name and an argument shape.

    Pure data. It carries no callable and no registry handle, so handing it to
    the planner does not breach the planner/tools separation (spec D4).
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    name: str
    version: str
    summary: str
    required: list[str]
    optional: list[str]

    def render(self) -> str:
        args = ", ".join([*(f"{a}" for a in self.required), *(f"{a}?" for a in self.optional)])
        return f"{self.name}({args}) - {self.summary}"
