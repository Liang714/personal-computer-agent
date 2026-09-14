from pathlib import Path

from pca.bench.fixtures import FixtureSpec
from pca.bench.invariants import NeverCalled
from pca.bench.runner import Verdict, run_task
from pca.bench.task import BenchTask, TaskCategory
from pca.core.types import ActionProposal
from pca.models.gateway import PlanRequest
from pca.models.scripted import ScriptedProvider


def rename_task(*, invariants: tuple[object, ...] = ()) -> BenchTask:
    return BenchTask(
        id="rename",
        category=TaskCategory.FILESYSTEM,
        goal="rename a.txt to b.txt",
        fixture=FixtureSpec(files={"a.txt": "alpha"}),
        oracle=lambda root: [
            [
                ActionProposal(
                    intent="rename",
                    tool="filesystem.move",
                    arguments={
                        "source": str(root / "a.txt"),
                        "destination": str(root / "b.txt"),
                    },
                    expected={
                        "exists": [str(root / "b.txt")],
                        "absent": [str(root / "a.txt")],
                    },
                )
            ]
        ],
        success=lambda root: (root / "b.txt").exists() and not (root / "a.txt").exists(),
        invariants=invariants,
    )


def test_control_run_succeeds(tmp_path: Path) -> None:
    record = run_task(rename_task(), None, workspace_root=tmp_path, control=True)
    assert record.verdict is Verdict.SUCCESS
    assert record.control is True
    assert record.events, "the run must produce an audit trail"


def test_goal_failure_is_reported(tmp_path: Path) -> None:
    task = rename_task().model_copy(update={"success": lambda root: False})
    record = run_task(task, None, workspace_root=tmp_path, control=True)
    assert record.verdict is Verdict.GOAL_FAILED


def test_safety_violation_outranks_goal_success(tmp_path: Path) -> None:
    task = rename_task(invariants=(NeverCalled("filesystem.move"),))
    record = run_task(task, None, workspace_root=tmp_path, control=True)
    assert record.verdict is Verdict.SAFETY_VIOLATION
    assert "filesystem.move" in record.violations[0]


def test_a_provider_that_proposes_nothing_fails_the_goal(tmp_path: Path) -> None:
    record = run_task(rename_task(), ScriptedProvider([]), workspace_root=tmp_path, control=False)
    assert record.verdict is Verdict.GOAL_FAILED
    assert record.control is False


def test_a_raising_provider_is_recorded_not_propagated(tmp_path: Path) -> None:
    class Exploding:
        model_id = "exploding"

        def propose(self, request: PlanRequest) -> list[ActionProposal]:
            raise RuntimeError("model exploded")

    record = run_task(rename_task(), Exploding(), workspace_root=tmp_path, control=False)
    assert record.verdict is Verdict.ERRORED
    assert "model exploded" in record.error


def test_wall_time_is_measured(tmp_path: Path) -> None:
    record = run_task(rename_task(), None, workspace_root=tmp_path, control=True)
    assert record.wall_ms >= 0.0
