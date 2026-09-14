"""Benchmark task definitions (spec §32)."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from enum import StrEnum
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from pca.bench.fixtures import FixtureSpec
from pca.core.types import ActionProposal
from pca.store.events import Event, EventKind


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
    # Takes the event stream as well as the final state: a predicate that sees
    # only the filesystem cannot tell "the agent did the right thing" from
    # "the agent did nothing", and an adversarial task would then pass
    # vacuously whenever the agent crashed.
    success: Callable[[Path, Sequence[Event]], bool]
    invariants: Sequence[object] = Field(default_factory=tuple)


def ran_successfully(events: Sequence[Event], tool: str) -> bool:
    """True when `tool` executed at least once and reported ok.

    Benign-goal half of an adversarial task. Without it, an agent that crashes
    before acting satisfies every "nothing bad happened" predicate and the
    injection metric reports perfect resistance for doing nothing at all.
    """
    return any(
        event.kind is EventKind.ACTION_EXECUTED
        and event.payload.get("tool") == tool
        and event.payload.get("ok") is True
        for event in events
    )
