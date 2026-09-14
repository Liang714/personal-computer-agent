import pytest

from pca.broker.approval import (
    AlwaysApprove,
    AlwaysDeny,
    ApprovalRequest,
    ScriptedApproval,
    describe,
)
from pca.core.types import RiskLevel


@pytest.fixture
def request_() -> ApprovalRequest:
    return ApprovalRequest(
        intent="clear old downloads",
        tool="filesystem.delete",
        target="12 files in ~/Downloads",
        consequence="12 files move to the agent trash",
        reversible=True,
        reason="delete is classified HIGH risk",
        risk=RiskLevel.HIGH,
    )


def test_description_names_every_required_element(request_: ApprovalRequest) -> None:
    text = describe(request_)
    assert "filesystem.delete" in text
    assert "12 files in ~/Downloads" in text
    assert "move to the agent trash" in text
    assert "Reversible" in text
    assert "HIGH" in text.upper()


def test_description_is_never_a_bare_prompt(request_: ApprovalRequest) -> None:
    assert len(describe(request_).splitlines()) >= 5


def test_always_deny_refuses(request_: ApprovalRequest) -> None:
    assert AlwaysDeny().request(request_) is False


def test_always_approve_accepts(request_: ApprovalRequest) -> None:
    assert AlwaysApprove().request(request_) is True


def test_scripted_approval_replays_decisions(request_: ApprovalRequest) -> None:
    ui = ScriptedApproval([True, False])
    assert ui.request(request_) is True
    assert ui.request(request_) is False


def test_scripted_approval_denies_when_exhausted(request_: ApprovalRequest) -> None:
    ui = ScriptedApproval([])
    assert ui.request(request_) is False
