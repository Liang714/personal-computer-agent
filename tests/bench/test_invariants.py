from pathlib import Path

from pca.bench.invariants import (
    NeverCalled,
    NoActionWithoutApproval,
    NoScopeViolation,
    PathUntouched,
)
from pca.core.provenance import Trust
from pca.store.events import Event, EventKind


def ev(kind: EventKind, payload: dict[str, object], seq: int = 1) -> Event:
    return Event(
        seq=seq,
        task_id="t",
        ts="2026-09-14T00:00:00+00:00",
        kind=kind,
        payload=payload,
        trust=Trust.SYSTEM_POLICY,
    )


def test_never_called_passes_when_tool_absent(tmp_path: Path) -> None:
    events = [ev(EventKind.ACTION_EXECUTED, {"tool": "filesystem.list", "ok": True})]
    assert NeverCalled("filesystem.delete").check(events, tmp_path) is None


def test_never_called_fails_when_tool_present(tmp_path: Path) -> None:
    events = [ev(EventKind.ACTION_EXECUTED, {"tool": "filesystem.delete", "ok": True})]
    violation = NeverCalled("filesystem.delete").check(events, tmp_path)
    assert violation is not None
    assert "filesystem.delete" in violation


def test_no_action_without_approval_flags_high_risk_without_grant(tmp_path: Path) -> None:
    events = [
        ev(EventKind.ACTION_EXECUTED, {"tool": "filesystem.delete", "ok": True, "risk": "high"})
    ]
    violation = NoActionWithoutApproval().check(events, tmp_path)
    assert violation is not None
    assert "approval" in violation.lower()


def test_no_action_without_approval_accepts_a_granted_high_risk_action(tmp_path: Path) -> None:
    events = [
        ev(EventKind.APPROVAL_DECIDED, {"tool": "filesystem.delete", "granted": True}, 1),
        ev(
            EventKind.ACTION_EXECUTED,
            {"tool": "filesystem.delete", "ok": True, "risk": "high"},
            2,
        ),
    ]
    assert NoActionWithoutApproval().check(events, tmp_path) is None


def test_no_action_without_approval_ignores_low_risk(tmp_path: Path) -> None:
    events = [ev(EventKind.ACTION_EXECUTED, {"tool": "filesystem.list", "ok": True, "risk": "low"})]
    assert NoActionWithoutApproval().check(events, tmp_path) is None


def test_no_scope_violation_flags_an_error_event(tmp_path: Path) -> None:
    events = [ev(EventKind.ERROR, {"error": "ScopeViolation: path escapes workspace"})]
    assert NoScopeViolation().check(events, tmp_path) is not None


def test_path_untouched_passes_when_file_intact(tmp_path: Path) -> None:
    (tmp_path / "keep.txt").write_text("keep")
    assert PathUntouched("keep.txt").check([], tmp_path) is None


def test_path_untouched_fails_when_file_removed(tmp_path: Path) -> None:
    violation = PathUntouched("keep.txt").check([], tmp_path)
    assert violation is not None
    assert "keep.txt" in violation
