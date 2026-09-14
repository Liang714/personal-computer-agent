from pathlib import Path

from pca.bench.fixtures import FixtureSpec, build_fixture
from pca.bench.task import COVERED_CATEGORIES, TaskCategory


def test_fixture_creates_declared_files(tmp_path: Path) -> None:
    build_fixture(FixtureSpec(files={"a.txt": "alpha", "sub/b.txt": "beta"}), tmp_path)
    assert (tmp_path / "a.txt").read_text() == "alpha"
    assert (tmp_path / "sub" / "b.txt").read_text() == "beta"


def test_fixture_creates_empty_dirs(tmp_path: Path) -> None:
    build_fixture(FixtureSpec(dirs=["empty"]), tmp_path)
    assert (tmp_path / "empty").is_dir()


def test_fixture_is_deterministic(tmp_path: Path) -> None:
    spec = FixtureSpec(files={"a.txt": "alpha", "b.txt": "beta"})
    first, second = tmp_path / "one", tmp_path / "two"
    first.mkdir()
    second.mkdir()
    build_fixture(spec, first)
    build_fixture(spec, second)

    def listing(base: Path) -> list[tuple[str, str]]:
        return sorted(
            (q.relative_to(base).as_posix(), q.read_text()) for q in base.rglob("*") if q.is_file()
        )

    assert listing(first) == listing(second)


def test_uncovered_categories_are_declared_but_not_covered() -> None:
    assert TaskCategory.BROWSER not in COVERED_CATEGORIES
    assert TaskCategory.MACOS not in COVERED_CATEGORIES
    assert TaskCategory.FILESYSTEM in COVERED_CATEGORIES
