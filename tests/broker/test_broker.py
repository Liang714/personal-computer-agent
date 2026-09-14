from pathlib import Path

import pytest

from pca.agent.limits import Budget, BudgetTracker
from pca.broker.approval import AlwaysApprove, AlwaysDeny, ScriptedApproval
from pca.broker.broker import CapabilityBroker
from pca.core.errors import (
    ApprovalRefused,
    BudgetExhausted,
    PolicyViolation,
    SchemaRejected,
    ScopeViolation,
)
from pca.core.types import ActionProposal, Capability, Permission
from pca.policy.paths import Workspace
from pca.policy.permissions import PermissionPolicy
from pca.store.events import EventKind, EventStore
from pca.tools.filesystem.delete import delete_tools
from pca.tools.filesystem.read import read_tools
from pca.tools.filesystem.write import write_tools
from pca.tools.registry import ToolRegistry


def build_broker(
    tmp_path: Path,
    *,
    approval: object | None = None,
    permissions: PermissionPolicy | None = None,
    budget: Budget | None = None,
) -> tuple[CapabilityBroker, Workspace]:
    root = tmp_path / "work"
    root.mkdir()
    (root / "a.txt").write_text("alpha")
    workspace = Workspace(roots=[root], trash=tmp_path / "trash")

    registry = ToolRegistry()
    for tool in (*read_tools(), *write_tools(), *delete_tools()):
        registry.register(tool)

    broker = CapabilityBroker(
        registry=registry,
        permissions=permissions or PermissionPolicy.default(),
        workspace=workspace,
        approval=approval or AlwaysApprove(),  # type: ignore[arg-type]
        store=EventStore(tmp_path / "audit.sqlite3"),
        budget=BudgetTracker(budget or Budget()),
    )
    return broker, workspace


def test_allowed_low_risk_action_executes_without_approval(tmp_path: Path) -> None:
    broker, ws = build_broker(tmp_path, approval=AlwaysDeny())
    proposal = ActionProposal(
        intent="see files", tool="filesystem.list", arguments={"path": str(ws.roots[0])}
    )
    result = broker.execute("t1", proposal)
    assert result.ok


def test_denied_capability_never_reaches_the_tool(tmp_path: Path) -> None:
    broker, ws = build_broker(
        tmp_path,
        permissions=PermissionPolicy({Capability.FILESYSTEM_READ: Permission.DENIED}),
    )
    proposal = ActionProposal(
        intent="see files", tool="filesystem.list", arguments={"path": str(ws.roots[0])}
    )
    with pytest.raises(PolicyViolation):
        broker.execute("t1", proposal)


def test_high_risk_action_is_blocked_when_approval_is_refused(tmp_path: Path) -> None:
    broker, ws = build_broker(tmp_path, approval=AlwaysDeny())
    proposal = ActionProposal(
        intent="remove file",
        tool="filesystem.delete",
        arguments={"paths": [str(ws.roots[0] / "a.txt")]},
    )
    with pytest.raises(ApprovalRefused):
        broker.execute("t1", proposal)
    assert (ws.roots[0] / "a.txt").exists(), "refused delete must not happen"


def test_delete_asks_for_approval_even_when_capability_is_allowed(tmp_path: Path) -> None:
    scripted = ScriptedApproval([False])
    broker, ws = build_broker(
        tmp_path,
        approval=scripted,
        permissions=PermissionPolicy({Capability.FILESYSTEM_DELETE: Permission.ALLOWED}),
    )
    proposal = ActionProposal(
        intent="remove file",
        tool="filesystem.delete",
        arguments={"paths": [str(ws.roots[0] / "a.txt")]},
    )
    with pytest.raises(ApprovalRefused):
        broker.execute("t1", proposal)


def test_unknown_tool_is_rejected_before_any_other_stage(tmp_path: Path) -> None:
    broker, _ = build_broker(tmp_path)
    with pytest.raises(SchemaRejected):
        broker.execute("t1", ActionProposal(intent="x", tool="shell.run", arguments={}))


def test_path_escape_is_rejected(tmp_path: Path) -> None:
    broker, _ = build_broker(tmp_path)
    proposal = ActionProposal(
        intent="read secrets", tool="filesystem.read_text", arguments={"path": "/etc/hosts"}
    )
    with pytest.raises(ScopeViolation):
        broker.execute("t1", proposal)


def test_budget_stops_execution(tmp_path: Path) -> None:
    broker, ws = build_broker(tmp_path, budget=Budget(max_actions=1))
    proposal = ActionProposal(
        intent="see files", tool="filesystem.list", arguments={"path": str(ws.roots[0])}
    )
    broker.execute("t1", proposal)
    with pytest.raises(BudgetExhausted):
        broker.execute("t1", proposal)


def test_every_stage_is_audited(tmp_path: Path) -> None:
    broker, ws = build_broker(tmp_path)
    proposal = ActionProposal(
        intent="see files", tool="filesystem.list", arguments={"path": str(ws.roots[0])}
    )
    broker.execute("t1", proposal)
    kinds = [e.kind for e in broker.store.events("t1")]
    assert EventKind.POLICY_CHECKED in kinds
    assert EventKind.RISK_CLASSIFIED in kinds
    assert EventKind.ACTION_EXECUTED in kinds


def test_refusal_is_audited_too(tmp_path: Path) -> None:
    broker, ws = build_broker(tmp_path, approval=AlwaysDeny())
    proposal = ActionProposal(
        intent="remove file",
        tool="filesystem.delete",
        arguments={"paths": [str(ws.roots[0] / "a.txt")]},
    )
    with pytest.raises(ApprovalRefused):
        broker.execute("t1", proposal)
    kinds = [e.kind for e in broker.store.events("t1")]
    assert EventKind.APPROVAL_DECIDED in kinds


def test_cancellation_stops_before_execution(tmp_path: Path) -> None:
    broker, ws = build_broker(tmp_path)
    broker.budget.cancel()
    proposal = ActionProposal(
        intent="see files", tool="filesystem.list", arguments={"path": str(ws.roots[0])}
    )
    with pytest.raises(BudgetExhausted, match="cancelled"):
        broker.execute("t1", proposal)


def test_a_raw_os_error_from_a_tool_becomes_a_typed_error(tmp_path: Path) -> None:
    """Listing a file as if it were a directory raises NotADirectoryError.

    A real model did exactly this. Because OSError is not an AgentError, it
    escaped the state machine and killed the task instead of being classified
    and recovered.
    """
    from pca.core.errors import ToolExecutionError

    broker, ws = build_broker(tmp_path)
    proposal = ActionProposal(
        intent="list a file by mistake",
        tool="filesystem.list",
        arguments={"path": str(ws.roots[0] / "a.txt")},
    )
    with pytest.raises(ToolExecutionError, match="filesystem.list failed"):
        broker.execute("t1", proposal)
