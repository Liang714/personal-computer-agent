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


def _resolve_destination(workspace: Workspace, raw: str, source: Path | None = None) -> Path:
    """Resolve a destination that may not exist yet.

    The parent is resolved (which enforces workspace containment) and the leaf
    rejoined, because `Workspace.resolve` requires a path to exist.

    When the destination is an existing directory and a source is given, the
    target becomes `destination/source.name` - the universal `mv file dir/`
    convention. Without this, a model proposing `move a.pdf -> PDF` was refused
    with "destination exists", which is what made qwen3:14b fail the multi-step
    organise task on every repeat.
    """
    candidate = Path(raw).expanduser()
    parent = workspace.resolve(str(candidate.parent))
    target = parent / candidate.name
    if source is not None and target.is_dir():
        return target / source.name
    return target


class MkdirTool(Tool):
    """Create a directory, including any missing parents."""

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
    """Move or rename a file. Destination may be a folder. No rename tool exists."""

    name = "filesystem.move"
    version = "1"
    capability = Capability.FILESYSTEM_WRITE
    base_risk = RiskLevel.MEDIUM
    Input = TransferIn
    Output = TransferOut

    def run(self, args: BaseModel, workspace: Workspace) -> ToolResult:
        assert isinstance(args, TransferIn)
        source = workspace.resolve(args.source)
        destination = _resolve_destination(workspace, args.destination, source)
        if destination.exists():
            return ToolResult(ok=False, data={"error": f"destination exists: {destination}"})
        shutil.move(str(source), str(destination))
        return ToolResult(ok=True, data={"source": str(source), "destination": str(destination)})


class CopyTool(Tool):
    """Copy a file or directory, leaving the source. Destination may be a folder."""

    name = "filesystem.copy"
    version = "1"
    capability = Capability.FILESYSTEM_WRITE
    base_risk = RiskLevel.MEDIUM
    Input = TransferIn
    Output = TransferOut

    def run(self, args: BaseModel, workspace: Workspace) -> ToolResult:
        assert isinstance(args, TransferIn)
        source = workspace.resolve(args.source)
        destination = _resolve_destination(workspace, args.destination, source)
        if destination.exists():
            return ToolResult(ok=False, data={"error": f"destination exists: {destination}"})
        if source.is_dir():
            shutil.copytree(source, destination)
        else:
            shutil.copy2(source, destination)
        return ToolResult(ok=True, data={"source": str(source), "destination": str(destination)})


def write_tools() -> list[Tool]:
    return [MkdirTool(), MoveTool(), CopyTool()]
