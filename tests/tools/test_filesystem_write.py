from pathlib import Path

import pytest

from pca.core.errors import ScopeViolation
from pca.core.types import RiskLevel
from pca.policy.paths import Workspace
from pca.tools.filesystem.write import CopyTool, MkdirTool, MoveTool


@pytest.fixture
def ws(tmp_path: Path) -> Workspace:
    root = tmp_path / "work"
    root.mkdir()
    (root / "a.txt").write_text("alpha")
    return Workspace(roots=[root], trash=tmp_path / "trash")


def test_mkdir_creates_a_directory(ws: Workspace) -> None:
    tool = MkdirTool()
    args = tool.Input.model_validate({"path": str(ws.roots[0] / "new")})
    result = tool.run(args, ws)
    assert result.ok
    assert (ws.roots[0] / "new").is_dir()


def test_move_relocates_a_file(ws: Workspace) -> None:
    tool = MoveTool()
    args = tool.Input.model_validate(
        {"source": str(ws.roots[0] / "a.txt"), "destination": str(ws.roots[0] / "b.txt")}
    )
    result = tool.run(args, ws)
    assert result.ok
    assert not (ws.roots[0] / "a.txt").exists()
    assert (ws.roots[0] / "b.txt").read_text() == "alpha"


def test_move_refuses_destination_outside_workspace(ws: Workspace, tmp_path: Path) -> None:
    tool = MoveTool()
    args = tool.Input.model_validate(
        {"source": str(ws.roots[0] / "a.txt"), "destination": str(tmp_path / "escaped.txt")}
    )
    with pytest.raises(ScopeViolation):
        tool.run(args, ws)


def test_move_refuses_to_overwrite_by_default(ws: Workspace) -> None:
    (ws.roots[0] / "b.txt").write_text("beta")
    tool = MoveTool()
    args = tool.Input.model_validate(
        {"source": str(ws.roots[0] / "a.txt"), "destination": str(ws.roots[0] / "b.txt")}
    )
    result = tool.run(args, ws)
    assert result.ok is False
    assert "exists" in result.data["error"]
    assert (ws.roots[0] / "b.txt").read_text() == "beta"


def test_copy_leaves_the_source_in_place(ws: Workspace) -> None:
    tool = CopyTool()
    args = tool.Input.model_validate(
        {"source": str(ws.roots[0] / "a.txt"), "destination": str(ws.roots[0] / "c.txt")}
    )
    result = tool.run(args, ws)
    assert result.ok
    assert (ws.roots[0] / "a.txt").exists()
    assert (ws.roots[0] / "c.txt").read_text() == "alpha"


def test_write_tools_are_medium_risk() -> None:
    assert MoveTool.base_risk is RiskLevel.MEDIUM
    assert CopyTool.base_risk is RiskLevel.MEDIUM


def test_move_into_an_existing_directory(ws: Workspace) -> None:
    """`mv file dir/` is universal convention, and what a model naturally writes.

    Measured: qwen3:14b failed the multi-step organise task on all three
    repeats because it proposed `move a.pdf -> PDF`, and the tool refused with
    "destination exists" instead of moving the file into the folder.
    """
    (ws.roots[0] / "PDF").mkdir()
    tool = MoveTool()
    args = tool.Input.model_validate({"source": "a.txt", "destination": "PDF"})
    result = tool.run(args, ws)

    assert result.ok, result.data.get("error")
    assert (ws.roots[0] / "PDF" / "a.txt").read_text() == "alpha"
    assert not (ws.roots[0] / "a.txt").exists()


def test_move_into_a_directory_still_refuses_to_clobber(ws: Workspace) -> None:
    """Directory semantics must not become an overwrite loophole."""
    (ws.roots[0] / "PDF").mkdir()
    (ws.roots[0] / "PDF" / "a.txt").write_text("already here")
    tool = MoveTool()
    args = tool.Input.model_validate({"source": "a.txt", "destination": "PDF"})
    result = tool.run(args, ws)

    assert result.ok is False
    assert "exists" in result.data["error"]
    assert (ws.roots[0] / "PDF" / "a.txt").read_text() == "already here"
    assert (ws.roots[0] / "a.txt").exists(), "a refused move must not remove the source"


def test_copy_into_an_existing_directory(ws: Workspace) -> None:
    (ws.roots[0] / "backup").mkdir()
    tool = CopyTool()
    args = tool.Input.model_validate({"source": "a.txt", "destination": "backup"})
    result = tool.run(args, ws)

    assert result.ok, result.data.get("error")
    assert (ws.roots[0] / "backup" / "a.txt").read_text() == "alpha"
    assert (ws.roots[0] / "a.txt").exists(), "copy must leave the source in place"
