"""Reversible delete (decision D5).

Nothing is unlinked. Targets move to a timestamped batch inside the workspace
trash, so the action is auditable and reversible.
"""

from __future__ import annotations

import shutil
from datetime import UTC, datetime
from pathlib import Path

from pydantic import BaseModel, ConfigDict

from pca.core.types import Capability, RiskLevel, ToolResult
from pca.policy.paths import Workspace
from pca.tools.base import Tool

_STRICT = ConfigDict(extra="forbid")


class DeleteIn(BaseModel):
    model_config = _STRICT
    paths: list[str]


class DeleteOut(BaseModel):
    model_config = _STRICT
    trashed: list[str]


class DeleteTool(Tool):
    """Move paths to the agent trash. High risk; always needs approval."""

    name = "filesystem.delete"
    version = "1"
    capability = Capability.FILESYSTEM_DELETE
    base_risk = RiskLevel.HIGH
    Input = DeleteIn
    Output = DeleteOut

    def run(self, args: BaseModel, workspace: Workspace) -> ToolResult:
        assert isinstance(args, DeleteIn)

        # Resolve and check everything before moving anything: a partially
        # applied delete is far worse than a refused one.
        targets: list[Path] = []
        for raw in args.paths:
            resolved = workspace.resolve(raw)
            if not resolved.exists():
                return ToolResult(ok=False, data={"error": f"does not exist: {raw}"})
            targets.append(resolved)

        stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%f")
        batch = workspace.trash / stamp
        batch.mkdir(parents=True, exist_ok=True)

        trashed: list[str] = []
        for target in targets:
            destination = batch / target.name
            shutil.move(str(target), str(destination))
            trashed.append(str(destination))

        return ToolResult(ok=True, data={"trashed": trashed})


def delete_tools() -> list[Tool]:
    return [DeleteTool()]
