"""Typed error hierarchy. Recovery dispatches on these types (spec §6)."""

from __future__ import annotations


class AgentError(Exception):
    """Base for every error the agent raises deliberately."""


class PolicyViolation(AgentError):
    """A capability was denied by the permission policy."""


class ScopeViolation(PolicyViolation):
    """A path or target fell outside the allowed workspace."""


class SchemaRejected(AgentError):
    """A proposal named an unknown tool or supplied invalid arguments."""


class ApprovalRefused(AgentError):
    """The user declined the action. Never retried."""


class VerificationFailed(AgentError):
    """A postcondition did not hold after execution."""


class AmbiguousTarget(AgentError):
    """Multiple candidates matched where one was expected. Stop, never guess."""


class BudgetExhausted(AgentError):
    """A hard limit from spec §10 was reached."""


class ToolExecutionError(AgentError):
    """A tool failed for a transient or environmental reason."""
