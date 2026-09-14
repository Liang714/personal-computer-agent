"""The capability broker: the single chokepoint for every action (spec §3, D1).

No other module holds both a tool registry and the ability to run a tool. The
stage order here is the security property; it is not a suggestion.
"""

from __future__ import annotations

from pca.agent.limits import BudgetTracker
from pca.broker.approval import ApprovalRequest, ApprovalUI
from pca.core.errors import ApprovalRefused, BudgetExhausted
from pca.core.types import ActionProposal, RiskLevel, ToolResult
from pca.policy.paths import Workspace
from pca.policy.permissions import PermissionPolicy
from pca.policy.risk import classify, requires_approval
from pca.store.events import EventKind, EventStore
from pca.tools.registry import ToolRegistry

_REVERSIBLE_TOOLS = {"filesystem.delete", "filesystem.copy", "filesystem.mkdir"}


class CapabilityBroker:
    def __init__(
        self,
        *,
        registry: ToolRegistry,
        permissions: PermissionPolicy,
        workspace: Workspace,
        approval: ApprovalUI,
        store: EventStore,
        budget: BudgetTracker,
    ) -> None:
        self._registry = registry
        self._permissions = permissions
        self._workspace = workspace
        self._approval = approval
        self.store = store
        self.budget = budget

    def tool_names(self) -> list[str]:
        """The tool vocabulary the planner is allowed to draw from."""
        return self._registry.names()

    def execute(self, task_id: str, proposal: ActionProposal) -> ToolResult:
        """Run one action through every gate, in order, auditing each stage."""
        if self.budget.cancelled:
            raise BudgetExhausted("task was cancelled by the user")
        self.budget.check_time()

        # 1. Resolve and validate. An unknown tool or bad argument stops here.
        tool, args = self._registry.resolve(proposal)
        self.store.append(
            task_id,
            EventKind.PLANNED,
            {"tool": tool.name, "version": tool.version, "intent": proposal.intent},
        )

        # 2. Permission. Raises PolicyViolation if the capability is denied.
        permission = self._permissions.require_not_denied(tool.capability)
        self.store.append(
            task_id,
            EventKind.POLICY_CHECKED,
            {"capability": tool.capability.value, "permission": permission.value},
        )

        # 3. Risk, from the resolved tool and validated arguments only.
        risk = classify(tool.name, args.model_dump(), tool.base_risk)
        self.store.append(
            task_id, EventKind.RISK_CLASSIFIED, {"tool": tool.name, "risk": risk.value}
        )

        # 4. Approval.
        if requires_approval(risk, permission):
            granted = self._ask(task_id, proposal, tool.name, risk)
            if not granted:
                raise ApprovalRefused(f"user declined: {tool.name}")

        # 5. Budget, charged only once the action is actually going to run.
        self.budget.charge_action()

        # 6. Execute.
        result = tool.run(args, self._workspace)
        self.store.append(
            task_id,
            EventKind.ACTION_EXECUTED,
            {"tool": tool.name, "ok": result.ok, "risk": risk.value},
            trust=result.trust,
        )
        return result

    def _ask(self, task_id: str, proposal: ActionProposal, tool_name: str, risk: RiskLevel) -> bool:
        request = ApprovalRequest(
            intent=proposal.intent,
            tool=tool_name,
            target=_describe_target(proposal),
            consequence=_describe_consequence(tool_name),
            reversible=tool_name in _REVERSIBLE_TOOLS,
            reason=f"{tool_name} is classified {risk.value.upper()} risk",
            risk=risk,
        )
        self.store.append(
            task_id, EventKind.APPROVAL_REQUESTED, {"tool": tool_name, "risk": risk.value}
        )
        granted = self._approval.request(request)
        self.store.append(
            task_id, EventKind.APPROVAL_DECIDED, {"tool": tool_name, "granted": granted}
        )
        return granted


def _describe_target(proposal: ActionProposal) -> str:
    for key in ("paths", "path", "source"):
        value = proposal.arguments.get(key)
        if isinstance(value, list):
            return f"{len(value)} path(s): {', '.join(str(v) for v in value[:3])}"
        if value is not None:
            return str(value)
    return "(no explicit target)"


def _describe_consequence(tool_name: str) -> str:
    return {
        "filesystem.delete": "targets move to the agent trash directory",
        "filesystem.move": "the file is relocated and no longer at its old path",
        "filesystem.copy": "a duplicate is created",
        "filesystem.mkdir": "a new directory is created",
    }.get(tool_name, "the tool runs against the target")
