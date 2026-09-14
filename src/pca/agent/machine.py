"""The task state machine (spec §10).

Proposals arrive in batches but execute strictly one at a time, with a fresh
verification between each. A batch whose step does not verify is abandoned:
the agent re-plans from what it observed, not from what it assumed.
"""

from __future__ import annotations

import json
import uuid
from collections.abc import Callable, Sequence
from enum import StrEnum

from pydantic import BaseModel, ConfigDict

from pca.broker.broker import CapabilityBroker
from pca.core.errors import AgentError, AmbiguousTarget, ApprovalRefused
from pca.core.provenance import Tagged, Trust
from pca.core.types import ActionProposal, ToolResult
from pca.models.gateway import ModelProvider, PlanRequest
from pca.policy.paths import Workspace
from pca.store.events import EventKind
from pca.verify.filesystem import verify_filesystem

# Tool output is fenced before it reaches the model, but a huge blob still
# crowds out the instructions, so it is capped.
_MAX_RESULT_CHARS = 4000


class State(StrEnum):
    IDLE = "idle"
    UNDERSTAND = "understand"
    OBSERVE = "observe"
    PLAN = "plan"
    ACT = "act"
    VERIFY = "verify"
    RECOVER = "recover"
    ASK_USER = "ask_user"
    COMPLETE = "complete"
    FAILED = "failed"


class TaskOutcome(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    task_id: str
    state: State
    summary: str
    actions_taken: int


def _describe_result(proposal: ActionProposal, result: ToolResult) -> Tagged:
    """Feed a tool's output back to the planner, at the tool's own trust level.

    Without this the planner never sees what it read. The agent could not
    perform "read X and tell me Y" at all, and every adversarial task passed
    trivially because the injected payload never reached the model. The
    Tagged/Trust fencing was built exactly for this path and, until now,
    nothing used it.
    """
    body = json.dumps(result.data, default=str)
    if len(body) > _MAX_RESULT_CHARS:
        body = body[:_MAX_RESULT_CHARS] + f"... (truncated, {len(body)} chars total)"
    return Tagged(
        text=f"output of {proposal.tool}:\n{body}",
        trust=result.trust,
    )


def _describe_history(history: Sequence[str]) -> Tagged:
    """What has already been done in this task.

    Without this the planner re-observes an unchanged world each iteration and
    proposes the same action again. Measured: on the adversarial tasks both
    qwen3:0.6b and qwen3:14b executed filesystem.read_text twelve times in a
    row and ended on the model-call budget, never progressing. A read does not
    change the directory listing, so state alone cannot tell the planner it
    has already acted.
    """
    if not history:
        return Tagged(
            text="actions taken so far: none, this is the first step",
            trust=Trust.SYSTEM_POLICY,
        )
    lines = "\n".join(f"  {i + 1}. {entry}" for i, entry in enumerate(history))
    return Tagged(
        text=(
            f"actions already taken in this task ({len(history)}):\n{lines}\n"
            "Do not repeat an action that already succeeded. If the goal is met, "
            "return an empty proposals list."
        ),
        trust=Trust.SYSTEM_POLICY,
    )


def _default_observe(workspace: Workspace) -> list[Tagged]:
    """Describe the workspace as it is now.

    The listing matters as much as the root path: without seeing current
    contents the planner cannot tell an achieved goal from an unstarted one,
    so it re-proposes work until the budget stops it.
    """
    root = workspace.roots[0]
    entries: list[str] = []
    for path in sorted(root.rglob("*")):
        if path.is_dir():
            entries.append(f"  {path.relative_to(root)}/")
        else:
            entries.append(f"  {path.relative_to(root)} ({path.stat().st_size} bytes)")
    listing = "\n".join(entries) if entries else "  (empty)"
    return [
        Tagged(
            text=f"workspace root: {root}\ncurrent contents:\n{listing}",
            trust=Trust.SYSTEM_POLICY,
        )
    ]


class Agent:
    def __init__(
        self,
        *,
        broker: CapabilityBroker,
        provider: ModelProvider,
        workspace: Workspace,
        observe: Callable[[Workspace], list[Tagged]] | None = None,
    ) -> None:
        self.broker = broker
        self._provider = provider
        self._workspace = workspace
        self._observe = observe or _default_observe

    def run(self, goal: str, task_id: str | None = None) -> TaskOutcome:
        task_id = task_id or uuid.uuid4().hex[:12]
        store = self.broker.store
        store.append(task_id, EventKind.TASK_STARTED, {"goal": goal})

        actions = 0
        state = State.OBSERVE
        summary = "nothing to do"
        history: list[str] = []
        recent_output: list[Tagged] = []

        try:
            while True:
                observations = [
                    *self._observe(self._workspace),
                    _describe_history(history),
                    *recent_output,
                ]
                store.append(task_id, EventKind.OBSERVED, {"count": len(observations)})

                state = State.PLAN
                self.broker.budget.charge_model_call()
                store.append(
                    task_id,
                    EventKind.MODEL_CALLED,
                    {"provider": self._provider.model_id},
                )
                proposals = self._provider.propose(
                    PlanRequest(
                        goal=goal,
                        observations=observations,
                        tool_names=self.broker.tool_names(),
                        tool_specs=self.broker.tool_specs(),
                    )
                )
                store.append(
                    task_id,
                    EventKind.PLANNED,
                    {"proposals": len(proposals)},
                    trust=Trust.MODEL_GENERATED_PLAN,
                )
                if not proposals:
                    state = State.COMPLETE
                    summary = f"completed after {actions} action(s)"
                    break

                state = State.ACT
                proposal = proposals[0]
                result = self.broker.execute(task_id, proposal)
                actions += 1
                history.append(
                    f"{proposal.tool} {proposal.arguments} -> {'ok' if result.ok else 'failed'}"
                )
                # Only the most recent output: older blobs are already reflected
                # in the workspace listing and in the history lines above.
                recent_output = [_describe_result(proposal, result)]

                state = State.VERIFY
                verdict = verify_filesystem(proposal.expected, self._workspace)
                store.append(
                    task_id,
                    EventKind.VERIFIED,
                    {"status": verdict.status, "detail": verdict.detail},
                )
                if verdict.status == "failed":
                    # Abandon the rest of the batch; the world is not as planned.
                    store.append(
                        task_id,
                        EventKind.RECOVERY_ATTEMPTED,
                        {"reason": verdict.detail},
                    )
                    summary = f"stopped after verification failed: {verdict.detail}"
                    state = State.FAILED
                    break

        except ApprovalRefused as exc:
            state = State.FAILED
            summary = f"user declined the action: {exc}"
            store.append(
                task_id,
                EventKind.ERROR,
                {"error": str(exc), "error_type": type(exc).__name__},
            )
        except AmbiguousTarget as exc:
            state = State.ASK_USER
            summary = f"stopped rather than guessing: {exc}"
            store.append(
                task_id,
                EventKind.ERROR,
                {"error": str(exc), "error_type": type(exc).__name__},
            )
        except AgentError as exc:
            state = State.FAILED
            summary = f"{type(exc).__name__}: {exc}"
            store.append(
                task_id,
                EventKind.ERROR,
                {"error": str(exc), "error_type": type(exc).__name__},
            )

        store.append(
            task_id,
            EventKind.TASK_FINISHED,
            {"state": state.value, "actions": actions, "summary": summary},
        )
        return TaskOutcome(task_id=task_id, state=state, summary=summary, actions_taken=actions)
