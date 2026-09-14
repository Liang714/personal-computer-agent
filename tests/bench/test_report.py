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
