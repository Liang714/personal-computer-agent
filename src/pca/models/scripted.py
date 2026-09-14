"""Deterministic provider. Every test and CI run uses this one."""

from __future__ import annotations

from pca.core.types import ActionProposal
from pca.models.gateway import PlanRequest


class ScriptedProvider:
    """Replays a fixed script of proposal batches, then proposes nothing."""

    def __init__(self, script: list[list[ActionProposal]]) -> None:
        self._script = list(script)
        self._index = 0

    @property
    def model_id(self) -> str:
        return "scripted"

    def propose(self, request: PlanRequest) -> list[ActionProposal]:
        if self._index >= len(self._script):
            return []
        batch = self._script[self._index]
        self._index += 1
        return list(batch)
