from pca.core.types import Permission, RiskLevel
from pca.policy.risk import classify, requires_approval


def test_classify_never_lowers_the_declared_base_risk() -> None:
    assert classify("filesystem.delete", {"path": "a.txt"}, RiskLevel.HIGH) is RiskLevel.HIGH


def test_bulk_operations_escalate_risk() -> None:
    single = classify("filesystem.delete", {"paths": ["a"]}, RiskLevel.HIGH)
    bulk = classify("filesystem.delete", {"paths": ["a"] * 25}, RiskLevel.HIGH)
    assert bulk.rank > single.rank
    assert bulk is RiskLevel.CRITICAL


def test_read_is_low_risk() -> None:
    assert classify("filesystem.list", {"path": "."}, RiskLevel.LOW) is RiskLevel.LOW


def test_high_risk_always_requires_approval_even_when_allowed() -> None:
    assert requires_approval(RiskLevel.HIGH, Permission.ALLOWED) is True
    assert requires_approval(RiskLevel.CRITICAL, Permission.ALLOWED) is True


def test_ask_permission_requires_approval_at_any_risk() -> None:
    assert requires_approval(RiskLevel.LOW, Permission.ASK) is True


def test_low_risk_with_allowed_permission_needs_no_approval() -> None:
    assert requires_approval(RiskLevel.LOW, Permission.ALLOWED) is False
