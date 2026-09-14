from pathlib import Path

import pytest

from pca.policy.paths import Workspace
from pca.verify.filesystem import verify_filesystem


@pytest.fixture
def ws(tmp_path: Path) -> Workspace:
    root = tmp_path / "work"
    root.mkdir()
    (root / "new.txt").write_text("n")
    return Workspace(roots=[root], trash=tmp_path / "trash")


def test_success_when_postconditions_hold(ws: Workspace) -> None:
    result = verify_filesystem(
        {
            "exists": [str(ws.roots[0] / "new.txt")],
            "absent": [str(ws.roots[0] / "old.txt")],
        },
        ws,
    )
    assert result.status == "success"


def test_failure_when_an_expected_file_is_missing(ws: Workspace) -> None:
    result = verify_filesystem({"exists": [str(ws.roots[0] / "ghost.txt")]}, ws)
    assert result.status == "failed"
    assert "ghost.txt" in result.detail


def test_failure_when_a_file_that_should_be_gone_remains(ws: Workspace) -> None:
    result = verify_filesystem({"absent": [str(ws.roots[0] / "new.txt")]}, ws)
    assert result.status == "failed"
    assert "new.txt" in result.detail


def test_empty_expectation_is_ambiguous_not_success(ws: Workspace) -> None:
    result = verify_filesystem({}, ws)
    assert result.status == "ambiguous"


def test_out_of_scope_expectation_is_ambiguous(ws: Workspace) -> None:
    result = verify_filesystem({"exists": ["/etc/passwd"]}, ws)
    assert result.status == "ambiguous"
    assert "scope" in result.detail.lower()
