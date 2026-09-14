from pathlib import Path

from pca.agent.limits import Budget, BudgetTracker
from pca.agent.machine import Agent, State
from pca.broker.approval import AlwaysApprove, AlwaysDeny
from pca.broker.broker import CapabilityBroker
from pca.core.types import ActionProposal
from pca.models.scripted import ScriptedProvider
from pca.policy.paths import Workspace
from pca.policy.permissions import PermissionPolicy
from pca.store.events import EventKind, EventStore
from pca.tools.filesystem.delete import delete_tools
from pca.tools.filesystem.read import read_tools
from pca.tools.filesystem.write import write_tools
from pca.tools.registry import ToolRegistry


def build_agent(
    tmp_path: Path, script: list[list[ActionProposal]], *, approval: object | None = None
) -> tuple[Agent, Workspace]:
    root = tmp_path / "work"
    root.mkdir()
    (root / "a.txt").write_text("alpha")
    workspace = Workspace(roots=[root], trash=tmp_path / "trash")

    registry = ToolRegistry()
    for tool in (*read_tools(), *write_tools(), *delete_tools()):
        registry.register(tool)

    broker = CapabilityBroker(
        registry=registry,
        permissions=PermissionPolicy.default(),
        workspace=workspace,
        approval=approval or AlwaysApprove(),  # type: ignore[arg-type]
        store=EventStore(tmp_path / "audit.sqlite3"),
        budget=BudgetTracker(Budget()),
    )
    agent = Agent(broker=broker, provider=ScriptedProvider(script), workspace=workspace)
    return agent, workspace


def test_completes_when_the_plan_verifies(tmp_path: Path) -> None:
    root = tmp_path / "work"
    script = [
        [
            ActionProposal(
                intent="rename the file",
                tool="filesystem.move",
                arguments={
                    "source": str(root / "a.txt"),
                    "destination": str(root / "b.txt"),
                },
                expected={"exists": [str(root / "b.txt")], "absent": [str(root / "a.txt")]},
            )
        ]
    ]
    agent, ws = build_agent(tmp_path, script)
    outcome = agent.run("rename a.txt to b.txt")

    assert outcome.state is State.COMPLETE
    assert outcome.actions_taken == 1
    assert (ws.roots[0] / "b.txt").exists()


def test_empty_plan_completes_without_acting(tmp_path: Path) -> None:
    agent, _ = build_agent(tmp_path, [])
    outcome = agent.run("do nothing")
    assert outcome.state is State.COMPLETE
    assert outcome.actions_taken == 0


def test_refused_approval_fails_the_task_without_acting(tmp_path: Path) -> None:
    root = tmp_path / "work"
    script = [
        [
            ActionProposal(
                intent="remove the file",
                tool="filesystem.delete",
                arguments={"paths": [str(root / "a.txt")]},
                expected={"absent": [str(root / "a.txt")]},
            )
        ]
    ]
    agent, ws = build_agent(tmp_path, script, approval=AlwaysDeny())
    outcome = agent.run("delete a.txt")

    assert outcome.state is State.FAILED
    assert "declined" in outcome.summary
    assert (ws.roots[0] / "a.txt").exists()


def test_remaining_batch_is_discarded_when_verification_fails(tmp_path: Path) -> None:
    root = tmp_path / "work"
    script = [
        [
            ActionProposal(
                intent="move with a wrong expectation",
                tool="filesystem.move",
                arguments={
                    "source": str(root / "a.txt"),
                    "destination": str(root / "b.txt"),
                },
                expected={"exists": [str(root / "NEVER.txt")]},
            ),
            ActionProposal(
                intent="second step that must not run",
                tool="filesystem.mkdir",
                arguments={"path": str(root / "should_not_exist")},
            ),
        ]
    ]
    agent, ws = build_agent(tmp_path, script)
    agent.run("two steps")
    assert not (ws.roots[0] / "should_not_exist").exists()


def test_the_run_is_fully_audited(tmp_path: Path) -> None:
    agent, _ = build_agent(tmp_path, [])
    outcome = agent.run("do nothing")
    kinds = [e.kind for e in agent.broker.store.events(outcome.task_id)]
    assert kinds[0] is EventKind.TASK_STARTED
    assert kinds[-1] is EventKind.TASK_FINISHED


def test_observations_carry_the_action_history(tmp_path: Path) -> None:
    """Measured failure: without history the planner repeats itself forever.

    A read does not change the directory listing, so state alone cannot tell
    the planner it has already acted. Both qwen3:0.6b and qwen3:14b executed
    filesystem.read_text twelve times in a row on the adversarial tasks and
    ended on the model-call budget.
    """
    root = tmp_path / "work"
    seen: list[str] = []

    class Recorder:
        model_id = "stub/recorder"

        def __init__(self) -> None:
            self.calls = 0

        def propose(self, request: object) -> list[ActionProposal]:
            self.calls += 1
            seen.append("\n".join(t.text for t in request.observations))  # type: ignore[attr-defined]
            if self.calls > 1:
                return []
            return [
                ActionProposal(
                    intent="read it",
                    tool="filesystem.read_text",
                    arguments={"path": str(root / "a.txt")},
                    expected={"exists": [str(root / "a.txt")]},
                )
            ]

    agent, _ = build_agent(tmp_path, [])
    agent._provider = Recorder()  # type: ignore[assignment]
    agent.run("read a.txt")

    assert "this is the first step" in seen[0]
    assert "filesystem.read_text" in seen[1], "the second plan must see the first action"
    assert "Do not repeat" in seen[1]
