"""Contextual human approval (spec §17).

A prompt that says only "Allow?" is a failure of this module. Every request
names the action, its target, its consequence, and whether it can be undone.
"""

from __future__ import annotations

from typing import Protocol

from pydantic import BaseModel, ConfigDict

from pca.core.types import RiskLevel


class ApprovalRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    intent: str
    tool: str
    target: str
    consequence: str
    reversible: bool
    reason: str
    risk: RiskLevel


def describe(req: ApprovalRequest) -> str:
    undo = (
        "Reversible — targets move to the agent trash."
        if req.reversible
        else "NOT reversible — this cannot be undone."
    )
    return "\n".join(
        [
            f"The agent wants to: {req.intent}",
            f"  Action:       {req.tool}",
            f"  Target:       {req.target}",
            f"  Consequence:  {req.consequence}",
            f"  Risk:         {req.risk.value.upper()}",
            f"  {undo}",
            f"  Asking because: {req.reason}",
        ]
    )


class ApprovalUI(Protocol):
    def request(self, req: ApprovalRequest) -> bool: ...


class AlwaysDeny:
    """Default for unattended runs. Refusing is always the safe answer."""

    def request(self, req: ApprovalRequest) -> bool:
        return False


class AlwaysApprove:
    """Test double only. Never wire this into a real run."""

    def request(self, req: ApprovalRequest) -> bool:
        return True


class ScriptedApproval:
    """Replays a fixed sequence of decisions, then denies."""

    def __init__(self, decisions: list[bool]) -> None:
        self._decisions = list(decisions)
        self._index = 0

    def request(self, req: ApprovalRequest) -> bool:
        if self._index >= len(self._decisions):
            return False
        decision = self._decisions[self._index]
        self._index += 1
        return decision


class CliApproval:
    """Prompts on the terminal. Anything but an explicit yes is a refusal."""

    def request(self, req: ApprovalRequest) -> bool:
        print()
        print(describe(req))
        answer = input("  Continue? [y/N] ").strip().lower()
        return answer in {"y", "yes"}
