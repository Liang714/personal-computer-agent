"""Failure classification and recovery selection (spec §22).

The agent never blindly retries. Every retry path re-observes first, and
non-idempotent actions are never retried at all.
"""

from __future__ import annotations

from enum import StrEnum

from pca.core.errors import (
    AmbiguousTarget,
    ApprovalRefused,
    BudgetExhausted,
    PolicyViolation,
    SchemaRejected,
    ToolExecutionError,
    VerificationFailed,
)


class Strategy(StrEnum):
    STOP = "stop"
    ASK_USER = "ask_user"
    REOBSERVE_AND_REPLAN = "reobserve_and_replan"
    RETRY_AFTER_REOBSERVE = "retry_after_reobserve"


def choose(error: Exception, *, idempotent: bool) -> Strategy:
    if isinstance(error, ApprovalRefused | PolicyViolation | BudgetExhausted):
        # The user or the policy said no. Retrying is not recovery, it is nagging.
        return Strategy.STOP

    if isinstance(error, AmbiguousTarget):
        return Strategy.ASK_USER

    if isinstance(error, SchemaRejected | VerificationFailed):
        return Strategy.REOBSERVE_AND_REPLAN

    if isinstance(error, ToolExecutionError):
        return Strategy.RETRY_AFTER_REOBSERVE if idempotent else Strategy.REOBSERVE_AND_REPLAN

    # An error we did not anticipate is exactly when improvising is most dangerous.
    return Strategy.STOP
