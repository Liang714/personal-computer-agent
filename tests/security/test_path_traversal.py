"""Every one of these must be refused. A pass here is a real vulnerability."""

from pathlib import Path

import pytest

from pca.core.errors import ScopeViolation
from pca.policy.paths import Workspace

ATTACKS = [
    "/etc/passwd",
    "/etc/../etc/passwd",
    "../../../../etc/passwd",
    "~/Library/Keychains/login.keychain-db",
    "~/.ssh/id_rsa",
    "/System/Library/CoreServices/SystemVersion.plist",
    "/Users/someone-else/.aws/credentials",  # another user's directory (README §13)
    "..",
    "../",
    "./../../",
    "．．/etc/passwd",
]


@pytest.fixture
def ws(tmp_path: Path) -> Workspace:
    root = tmp_path / "work"
    root.mkdir()
    return Workspace(roots=[root], trash=tmp_path / "trash")


@pytest.mark.parametrize("attack", ATTACKS)
def test_traversal_attempt_is_refused(ws: Workspace, attack: str) -> None:
    with pytest.raises(ScopeViolation):
        ws.resolve(attack)


def test_symlink_farm_cannot_escape(ws: Workspace, tmp_path: Path) -> None:
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "secret.txt").write_text("s")

    hop1 = ws.roots[0] / "hop1"
    hop1.symlink_to(outside)
    hop2 = ws.roots[0] / "hop2"
    hop2.symlink_to(hop1)

    with pytest.raises(ScopeViolation):
        ws.resolve(str(hop2 / "secret.txt"))


def test_a_path_inside_the_root_is_still_allowed(ws: Workspace) -> None:
    (ws.roots[0] / "ok.txt").write_text("fine")
    assert ws.resolve(str(ws.roots[0] / "ok.txt")).name == "ok.txt"
