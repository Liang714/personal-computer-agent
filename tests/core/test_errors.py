from pca.core.errors import AgentError, PolicyViolation, ScopeViolation


def test_scope_violation_is_a_policy_violation() -> None:
    assert issubclass(ScopeViolation, PolicyViolation)
    assert issubclass(PolicyViolation, AgentError)


def test_errors_carry_a_user_facing_message() -> None:
    err = ScopeViolation("path escapes workspace: /etc/passwd")
    assert "escapes workspace" in str(err)
