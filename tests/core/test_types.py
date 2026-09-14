import pytest
from pydantic import ValidationError

from pca.core.provenance import Trust
from pca.core.types import ActionProposal, Capability, Permission, RiskLevel, ToolResult


def test_risk_levels_are_ordered() -> None:
    assert RiskLevel.LOW.rank < RiskLevel.MEDIUM.rank
    assert RiskLevel.MEDIUM.rank < RiskLevel.HIGH.rank
    assert RiskLevel.HIGH.rank < RiskLevel.CRITICAL.rank


def test_proposal_rejects_unknown_fields() -> None:
    with pytest.raises(ValidationError):
        ActionProposal(intent="i", tool="filesystem.list", arguments={}, risk="low")  # type: ignore[call-arg]


def test_proposal_is_frozen() -> None:
    p = ActionProposal(intent="i", tool="filesystem.list", arguments={})
    with pytest.raises(ValidationError):
        p.tool = "filesystem.delete"  # type: ignore[misc]


def test_tool_result_carries_trust() -> None:
    r = ToolResult(ok=True, data={"n": 1}, trust=Trust.TOOL_OUTPUT)
    assert r.trust is Trust.TOOL_OUTPUT


def test_permission_and_capability_are_string_enums() -> None:
    assert Permission.ASK == "ask"
    assert Capability.FILESYSTEM_DELETE == "filesystem_delete"
