from pathlib import Path

import pytest

from pca.bench.runner import Verdict, run_task
from pca.bench.suite import adversarial_tasks, all_tasks, filesystem_tasks
from pca.bench.task import BenchTask, TaskCategory


def test_suite_is_not_empty() -> None:
    assert len(all_tasks()) >= 5


def test_task_ids_are_unique() -> None:
    ids = [t.id for t in all_tasks()]
    assert len(ids) == len(set(ids))


def test_adversarial_tasks_carry_invariants() -> None:
    for task in adversarial_tasks():
        assert task.invariants, f"{task.id} must declare what it forbids"
        assert task.category is TaskCategory.ADVERSARIAL


def test_filesystem_tasks_are_filesystem_category() -> None:
    for task in filesystem_tasks():
        assert task.category is TaskCategory.FILESYSTEM


@pytest.mark.parametrize("task", all_tasks(), ids=lambda t: t.id)
def test_every_control_run_passes(task: BenchTask, tmp_path: Path) -> None:
    """A task whose own oracle fails is a broken task, not a model failure."""
    record = run_task(task, None, workspace_root=tmp_path, control=True)
    assert record.verdict is Verdict.SUCCESS, (
        f"control run for {record.task_id} failed: "
        f"{record.verdict.value} {record.violations} {record.error}"
    )
