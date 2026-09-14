from pathlib import Path

import pytest

from pca.core.errors import ScopeViolation
from pca.policy.paths import Workspace


@pytest.fixture
def ws(tmp_path: Path) -> Workspace:
    root = tmp_path / "work"
    root.mkdir()
    (root / "docs").mkdir()
    (root / "docs" / "a.txt").write_text("a")
    return Workspace(roots=[root], trash=tmp_path / "trash")


def test_resolves_a_path_inside_the_root(ws: Workspace, tmp_path: Path) -> None:
    assert ws.resolve(str(tmp_path / "work" / "docs" / "a.txt")).name == "a.txt"


def test_rejects_parent_traversal(ws: Workspace, tmp_path: Path) -> None:
    with pytest.raises(ScopeViolation):
        ws.resolve(str(tmp_path / "work" / ".." / "outside.txt"))


def test_rejects_absolute_path_outside_root(ws: Workspace) -> None:
    with pytest.raises(ScopeViolation):
        ws.resolve("/etc/passwd")


def test_rejects_symlink_escaping_root(ws: Workspace, tmp_path: Path) -> None:
    secret = tmp_path / "secret.txt"
    secret.write_text("s")
    link = tmp_path / "work" / "link.txt"
    link.symlink_to(secret)
    with pytest.raises(ScopeViolation):
        ws.resolve(str(link))


def test_rejects_tilde_expansion_outside_root(ws: Workspace) -> None:
    with pytest.raises(ScopeViolation):
        ws.resolve("~/Library/Keychains/login.keychain-db")


def test_rejects_unicode_normalisation_trick(ws: Workspace, tmp_path: Path) -> None:
    # U+FF0E FULLWIDTH FULL STOP must not be treated as a path separator dot.
    with pytest.raises(ScopeViolation):
        ws.resolve(str(tmp_path / "work" / "．．" / "outside.txt"))


def test_trash_is_inside_workspace_control(ws: Workspace) -> None:
    assert ws.trash.name == "trash"


def test_contains_reports_membership(ws: Workspace, tmp_path: Path) -> None:
    assert ws.contains(tmp_path / "work" / "docs")
    assert not ws.contains(Path("/etc"))


def test_relative_paths_anchor_to_the_workspace_not_the_cwd(ws: Workspace, tmp_path: Path) -> None:
    """A model naturally writes "a.txt", not an absolute path.

    Resolving that against the process CWD made it escape the workspace and be
    refused. Anchoring to the workspace root is both more usable and safer.
    """
    (ws.roots[0] / "rel.txt").write_text("here")
    assert ws.resolve("rel.txt") == ws.roots[0] / "rel.txt"
    assert ws.resolve("docs/a.txt") == ws.roots[0] / "docs" / "a.txt"


def test_relative_traversal_is_still_refused_after_anchoring(ws: Workspace) -> None:
    with pytest.raises(ScopeViolation):
        ws.resolve("../../../etc/passwd")
