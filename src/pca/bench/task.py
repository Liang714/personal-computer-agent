"""Benchmark task definitions (spec §32)."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from enum import StrEnum
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from pca.bench.fixtures import FixtureSpec
from pca.core.types import ActionProposal


class TaskCategory(StrEnum):
    FILESYSTEM = "filesystem"
    RECOVERY = "recovery"
    ADVERSARIAL = "adversarial"
    # Declared so the report can show them as uncovered rather than omit them.
    BROWSER = "browser"
    MACOS = "macos"
    CROSS_APP = "cross_app"


COVERED_CATEGORIES = frozenset(
    {TaskCategory.FILESYSTEM, TaskCategory.RECOVERY, TaskCategory.ADVERSARIAL}
)


class BenchTask(BaseModel):
    """One measurable task. `oracle` is the hand-written control plan (spec D5)."""

    model_config = ConfigDict(extra="forbid", frozen=True, arbitrary_types_allowed=True)

    id: str
    category: TaskCategory
    goal: str
    fixture: FixtureSpec
    oracle: Callable[[Path], list[list[ActionProposal]]]
    success: Callable[[Path], bool]
    invariants: Sequence[object] = Field(default_factory=tuple)
