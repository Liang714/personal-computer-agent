import json

from pca.bench.metrics import compute
from pca.bench.report import to_json, to_markdown
from pca.bench.runner import RunRecord, Verdict


def a_record(verdict: Verdict = Verdict.SUCCESS, task_id: str = "fs_rename") -> RunRecord:
    return RunRecord(
        task_id=task_id,
        category="filesystem",
        provider_id="ollama/qwen3:14b",
        verdict=verdict,
        actions_taken=1,
        wall_ms=12.5,
    )


def test_json_round_trips() -> None:
    records = [a_record()]
    payload = json.loads(to_json(records, compute(records)))
    assert payload["metrics"]["task_success_rate"] == 1.0
    assert payload["runs"][0]["task_id"] == "fs_rename"


def test_json_omits_the_event_blob() -> None:
    """Events are large and already in SQLite; the report links, not duplicates."""
    records = [a_record()]
    payload = json.loads(to_json(records, compute(records)))
    assert "events" not in payload["runs"][0]


def test_markdown_contains_the_headline_metrics() -> None:
    records = [a_record()]
    text = to_markdown(records, compute(records))
    assert "Task success rate" in text
    assert "Injection success rate" in text
    assert "ollama/qwen3:14b" in text


def test_markdown_names_uncovered_categories() -> None:
    records = [a_record()]
    text = to_markdown(records, compute(records))
    assert "browser" in text.lower()
    assert "not yet covered" in text.lower()


def test_markdown_flags_a_safety_violation_prominently() -> None:
    records = [a_record(Verdict.SAFETY_VIOLATION, "adv_injected_delete")]
    text = to_markdown(records, compute(records))
    assert "SAFETY" in text.upper()


def test_comparison_marks_direction_per_metric() -> None:
    """A safety metric rising is a regression, not an improvement.

    A naive "delta > 0 is good" rule would label a doubled unsafe-action rate
    as a win, which is the single most dangerous way for this report to lie.
    """
    from pca.bench.metrics import MetricSet
    from pca.bench.report import to_comparison_markdown

    baseline = MetricSet(runs=5, task_success_rate=0.2, unsafe_action_rate=0.0)
    current = MetricSet(runs=5, task_success_rate=0.6, unsafe_action_rate=0.4)
    text = to_comparison_markdown(baseline, current)

    success_row = next(ln for ln in text.splitlines() if "Task success rate" in ln)
    unsafe_row = next(ln for ln in text.splitlines() if "Unsafe action rate" in ln)
    assert "better" in success_row
    assert "WORSE" in unsafe_row


def test_comparison_marks_no_change() -> None:
    from pca.bench.metrics import MetricSet
    from pca.bench.report import to_comparison_markdown

    same = MetricSet(runs=5, task_success_rate=0.5)
    row = next(
        ln for ln in to_comparison_markdown(same, same).splitlines() if "Task success rate" in ln
    )
    assert "no change" in row
