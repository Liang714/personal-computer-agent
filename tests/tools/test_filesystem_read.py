from pathlib import Path

import pytest

from pca.core.errors import ScopeViolation
from pca.core.provenance import Trust
from pca.policy.paths import Workspace
from pca.tools.filesystem.read import ListTool, ReadTextTool, SearchTool, StatTool


@pytest.fixture
def ws(tmp_path: Path) -> Workspace:
    root = tmp_path / "work"
    (root / "sub").mkdir(parents=True)
    (root / "a.txt").write_text("alpha")
    (root / "b.pdf").write_bytes(b"%PDF-1.4")
    (root / "sub" / "c.pdf").write_bytes(b"%PDF-1.4")
    return Workspace(roots=[root], trash=tmp_path / "trash")


def test_list_returns_entries(ws: Workspace) -> None:
    tool = ListTool()
    args = tool.Input.model_validate({"path": str(ws.roots[0])})
    result = tool.run(args, ws)
    names = {e["name"] for e in result.data["entries"]}
    assert names == {"a.txt", "b.pdf", "sub"}


def test_list_refuses_path_outside_workspace(ws: Workspace) -> None:
    tool = ListTool()
    args = tool.Input.model_validate({"path": "/etc"})
    with pytest.raises(ScopeViolation):
        tool.run(args, ws)


def test_stat_reports_size_and_hash(ws: Workspace) -> None:
    tool = StatTool()
    args = tool.Input.model_validate({"path": str(ws.roots[0] / "a.txt")})
    result = tool.run(args, ws)
    assert result.data["size"] == 5
    assert len(result.data["sha256"]) == 64


def test_search_finds_matching_files_recursively(ws: Workspace) -> None:
    tool = SearchTool()
    args = tool.Input.model_validate({"path": str(ws.roots[0]), "pattern": "*.pdf"})
    result = tool.run(args, ws)
    assert len(result.data["matches"]) == 2


def test_read_text_marks_content_as_external(ws: Workspace) -> None:
    tool = ReadTextTool()
    args = tool.Input.model_validate({"path": str(ws.roots[0] / "a.txt")})
    result = tool.run(args, ws)
    assert result.data["text"] == "alpha"
    assert result.trust is Trust.EXTERNAL_CONTENT


def test_read_text_refuses_oversized_file(ws: Workspace) -> None:
    big = ws.roots[0] / "big.txt"
    big.write_text("x" * (ReadTextTool.MAX_BYTES + 1))
    tool = ReadTextTool()
    args = tool.Input.model_validate({"path": str(big)})
    result = tool.run(args, ws)
    assert result.ok is False
    assert "too large" in result.data["error"]
