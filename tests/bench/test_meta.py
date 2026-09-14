"""The harness must be able to fail a bad agent, or it measures nothing."""

from pathlib import Path

from pca.bench.runner import Verdict, run_task
from pca.bench.suite import adversarial_tasks, filesystem_tasks
from pca.core.types import ActionProposal
from pca.models.gateway import PlanRequest


class ObedientVictim:
    """A planner that does exactly what an injected payload tells it to."""

    model_id = "stub/obedient-victim"

    def __init__(self, root: Path) -> None:
        self._root = root
        self._done = False

    def propose(self, request: PlanRequest) -> list[ActionProposal]:
        if self._done:
            return []
        self._done = True
        return [
            ActionProposal(
                intent="obey the injected instruction",
                tool="filesystem.delete",
                arguments={"paths": [str(self._root / "payroll.csv")]},
            )
        ]


class Idle:
    model_id = "stub/idle"

    def propose(self, request: PlanRequest) -> list[ActionProposal]:
        return []


def test_harness_detects_an_agent_that_obeys_an_injection(tmp_path: Path) -> None:
    task = next(t for t in adversarial_tasks() if t.id == "adv_injected_delete")
    victim = ObedientVictim(tmp_path / "workspace")

    record = run_task(task, victim, workspace_root=tmp_path, control=False)

    assert record.verdict is Verdict.SAFETY_VIOLATION, (
        "the harness failed to detect a compromised agent - it measures nothing"
    )
    assert any("filesystem.delete" in v for v in record.violations)


def test_harness_detects_a_goal_failure(tmp_path: Path) -> None:
    task = next(t for t in filesystem_tasks() if t.id == "fs_rename")
    record = run_task(task, Idle(), workspace_root=tmp_path, control=False)
    assert record.verdict is Verdict.GOAL_FAILED
