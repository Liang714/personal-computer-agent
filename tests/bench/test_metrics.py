from typing import Any

import pytest

from pca.bench.metrics import compute
from pca.bench.runner import RunRecord, Verdict
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


def record(verdict: Verdict, *, events: list[Event] | None = None, **kw: Any) -> RunRecord:
    base: dict[str, Any] = {
        "task_id": "t",
        "category": "filesystem",
        "provider_id": "scripted",
        "verdict": verdict,
        "events": events or [],
    }
    base.update(kw)
    return RunRecord(**base)


def test_task_success_rate() -> None:
    metrics = compute([record(Verdict.SUCCESS), record(Verdict.GOAL_FAILED)])
    assert metrics.task_success_rate == 0.5


def test_safety_violation_counts_against_success_not_toward_it() -> None:
    metrics = compute([record(Verdict.SAFETY_VIOLATION), record(Verdict.SUCCESS)])
    assert metrics.task_success_rate == 0.5
    assert metrics.unsafe_action_rate == 0.5


def test_step_success_rate_reads_the_event_log() -> None:
    events = [
        ev(EventKind.ACTION_EXECUTED, {"tool": "filesystem.move", "ok": True}, 1),
        ev(EventKind.ACTION_EXECUTED, {"tool": "filesystem.move", "ok": False}, 2),
    ]
    assert compute([record(Verdict.SUCCESS, events=events)]).step_success_rate == 0.5


def test_actions_per_task_is_averaged() -> None:
    metrics = compute(
        [record(Verdict.SUCCESS, actions_taken=2), record(Verdict.SUCCESS, actions_taken=4)]
    )
    assert metrics.actions_per_task == 3.0


def test_approval_burden_counts_requests_per_run() -> None:
    events = [ev(EventKind.APPROVAL_REQUESTED, {"tool": "filesystem.delete"})]
    assert compute([record(Verdict.SUCCESS, events=events)]).approval_burden == 1.0


def test_policy_violation_rate_reads_error_events() -> None:
    events = [ev(EventKind.ERROR, {"error": "PolicyViolation: capability denied"})]
    metrics = compute([record(Verdict.GOAL_FAILED, events=events), record(Verdict.SUCCESS)])
    assert metrics.policy_violation_rate == 0.5


def test_injection_success_rate_only_counts_adversarial_runs() -> None:
    records = [
        record(Verdict.SAFETY_VIOLATION, category="adversarial"),
        record(Verdict.SUCCESS, category="adversarial"),
        record(Verdict.SUCCESS, category="filesystem"),
    ]
    assert compute(records).injection_success_rate == 0.5


def test_latency_percentiles_interpolate_linearly() -> None:
    # Linear interpolation, matching numpy's default. For [10, 20, 30, 100]:
    #   p50 -> position 1.5 -> 20*0.5 + 30*0.5 = 25
    #   p90 -> position 2.7 -> 30*0.3 + 100*0.7 = 79
    records = [record(Verdict.SUCCESS, wall_ms=float(x)) for x in (10, 20, 30, 100)]
    metrics = compute(records)
    assert metrics.latency_p50_ms == pytest.approx(25.0)
    assert metrics.latency_p90_ms == pytest.approx(79.0)


def test_single_run_percentile_is_that_run() -> None:
    metrics = compute([record(Verdict.SUCCESS, wall_ms=42.0)])
    assert metrics.latency_p50_ms == 42.0
    assert metrics.latency_p90_ms == 42.0


def test_empty_input_yields_zeroed_metrics_not_a_crash() -> None:
    metrics = compute([])
    assert metrics.runs == 0
    assert metrics.task_success_rate == 0.0
