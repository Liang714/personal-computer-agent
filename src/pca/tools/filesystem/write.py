"""Mutating filesystem capabilities. MEDIUM risk, workspace-scoped, non-clobbering."""

from __future__ import annotations

import shutil
from pathlib import Path

from pydantic import BaseModel, ConfigDict

from pca.core.types import Capability, RiskLevel, ToolResult
from pca.policy.paths import Workspace
from pca.tools.base import Tool

_STRICT = ConfigDict(extra="forbid")


class MkdirIn(BaseModel):
    model_config = _STRICT
    path: str


class TransferIn(BaseModel):
    model_config = _STRICT
    source: str
    destination: str


class PathOut(BaseModel):
    model_config = _STRICT
    path: str


class TransferOut(BaseModel):
    model_config = _STRICT
    source: str
    destination: str


def _resolve_destination(workspace: Workspace, raw: str) -> Path:
    """Destinations may not exist yet, so validate the parent then rejoin."""
    candidate = Path(raw).expanduser()
    parent = workspace.resolve(str(candidate.parent))
    return parent / candidate.name


class MkdirTool(Tool):
    name = "filesystem.mkdir"
    version = "1"
    capability = Capability.FILESYSTEM_WRITE
    base_risk = RiskLevel.MEDIUM
    Input = MkdirIn
    Output = PathOut

    def run(self, args: BaseModel, workspace: Workspace) -> ToolResult:
        assert isinstance(args, MkdirIn)
        target = _resolve_destination(workspace, args.path)
        target.mkdir(parents=True, exist_ok=True)
        return ToolResult(ok=True, data={"path": str(target)})


class MoveTool(Tool):
    name = "filesystem.move"
    version = "1"
    capability = Capability.FILESYSTEM_WRITE
    base_risk = RiskLevel.MEDIUM
    Input = TransferIn
    Output = TransferOut

    def run(self, args: BaseModel, workspace: Workspace) -> ToolResult:
        assert isinstance(args, TransferIn)
        source = workspace.resolve(args.source)
        destination = _resolve_destination(workspace, args.destination)
        if destination.exists():
            return ToolResult(ok=False, data={"error": f"destination exists: {destination}"})
        shutil.move(str(source), str(destination))
        return ToolResult(ok=True, data={"source": str(source), "destination": str(destination)})


class CopyTool(Tool):
    name = "filesystem.copy"
    version = "1"
    capability = Capability.FILESYSTEM_WRITE
    base_risk = RiskLevel.MEDIUM
    Input = TransferIn
    Output = TransferOut

    def run(self, args: BaseModel, workspace: Workspace) -> ToolResult:
        assert isinstance(args, TransferIn)
        source = workspace.resolve(args.source)
        destination = _resolve_destination(workspace, args.destination)
        if destination.exists():
            return ToolResult(ok=False, data={"error": f"destination exists: {destination}"})
        if source.is_dir():
            shutil.copytree(source, destination)
        else:
            shutil.copy2(source, destination)
        return ToolResult(ok=True, data={"source": str(source), "destination": str(destination)})


def write_tools() -> list[Tool]:
    return [MkdirTool(), MoveTool(), CopyTool()]
