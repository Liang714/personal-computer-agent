"""Deterministic benchmark workspaces (spec D4)."""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field


class FixtureSpec(BaseModel):
    """A workspace declared as data, so a task is reproducible from its id."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    files: dict[str, str] = Field(default_factory=dict)
    dirs: list[str] = Field(default_factory=list)


def build_fixture(spec: FixtureSpec, root: Path) -> None:
    """Populate `root`. Sorted so creation order never varies between runs."""
    root.mkdir(parents=True, exist_ok=True)
    for relative in sorted(spec.dirs):
        (root / relative).mkdir(parents=True, exist_ok=True)
    for relative, content in sorted(spec.files.items()):
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
