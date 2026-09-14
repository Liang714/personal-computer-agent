from pathlib import Path

import pytest

from pca.core.errors import ScopeViolation
from pca.core.types import Capability, RiskLevel
from pca.policy.paths import Workspace
from pca.tools.filesystem.delete import DeleteTool


@pytest.fixture
def ws(tmp_path: Path) -> Workspace:
    root = tmp_path / "work"
    root.mkdir()
    (root / "a.txt").write_text("alpha")
    (root / "b.txt").write_text("beta")
    return Workspace(roots=[root], trash=tmp_path / "trash")


def test_delete_is_high_risk_and_its_own_capability() -> None:
    assert DeleteTool.base_risk is RiskLevel.HIGH
    assert DeleteTool.capability is Capability.FILESYSTEM_DELETE


def test_delete_moves_to_trash_rather_than_unlinking(ws: Workspace) -> None:
    tool = DeleteTool()
    args = tool.Input.model_validate({"paths": [str(ws.roots[0] / "a.txt")]})
    result = tool.run(args, ws)

    assert result.ok
    assert not (ws.roots[0] / "a.txt").exists()
    trashed = Path(result.data["trashed"][0])
    assert trashed.exists()
    assert trashed.read_text() == "alpha"
    assert ws.trash in trashed.parents


def test_delete_handles_multiple_paths_in_one_batch(ws: Workspace) -> None:
    tool = DeleteTool()
    args = tool.Input.model_validate(
        {"paths": [str(ws.roots[0] / "a.txt"), str(ws.roots[0] / "b.txt")]}
    )
    result = tool.run(args, ws)
    assert len(result.data["trashed"]) == 2
    batch = Path(result.data["trashed"][0]).parent
    assert Path(result.data["trashed"][1]).parent == batch


def test_delete_refuses_path_outside_workspace(ws: Workspace) -> None:
    tool = DeleteTool()
    args = tool.Input.model_validate({"paths": ["/etc/passwd"]})
    with pytest.raises(ScopeViolation):
        tool.run(args, ws)


def test_delete_reports_missing_path_without_partial_effect(ws: Workspace) -> None:
    tool = DeleteTool()
    args = tool.Input.model_validate(
        {"paths": [str(ws.roots[0] / "a.txt"), str(ws.roots[0] / "ghost.txt")]}
    )
    result = tool.run(args, ws)
    assert result.ok is False
    assert "does not exist" in result.data["error"]
    assert (ws.roots[0] / "a.txt").exists(), "nothing should move if any target is bad"
