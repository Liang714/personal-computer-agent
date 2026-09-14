from pca.core.errors import (
    AmbiguousTarget,
    ApprovalRefused,
    BudgetExhausted,
    PolicyViolation,
    ScopeViolation,
    ToolExecutionError,
    VerificationFailed,
)
from pca.recovery.strategy import Strategy, choose


def test_approval_refusal_never_retries() -> None:
    assert choose(ApprovalRefused("no"), idempotent=True) is Strategy.STOP


def test_policy_and_scope_violations_stop() -> None:
    assert choose(PolicyViolation("denied"), idempotent=True) is Strategy.STOP
    assert choose(ScopeViolation("escape"), idempotent=True) is Strategy.STOP


def test_budget_exhaustion_stops() -> None:
    assert choose(BudgetExhausted("limit"), idempotent=True) is Strategy.STOP


def test_ambiguity_asks_the_user_rather_than_guessing() -> None:
    assert choose(AmbiguousTarget("two files"), idempotent=True) is Strategy.ASK_USER


def test_verification_failure_replans_from_fresh_observation() -> None:
    assert (
        choose(VerificationFailed("mismatch"), idempotent=False)
        is Strategy.REOBSERVE_AND_REPLAN
    )


def test_transient_tool_error_retries_only_when_idempotent() -> None:
    assert (
        choose(ToolExecutionError("timeout"), idempotent=True)
        is Strategy.RETRY_AFTER_REOBSERVE
    )
    assert (
        choose(ToolExecutionError("timeout"), idempotent=False)
        is Strategy.REOBSERVE_AND_REPLAN
    )


def test_unknown_error_stops_rather_than_improvising() -> None:
    assert choose(RuntimeError("???"), idempotent=True) is Strategy.STOP
