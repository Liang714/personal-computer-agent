import json
from pathlib import Path

import pytest

from pca.cli import main


def test_bench_runs_the_control_suite(tmp_path: Path) -> None:
    out_json = tmp_path / "report.json"
    code = main(
        [
            "bench",
            "--model",
            "scripted",
            "--json",
            str(out_json),
            "--workdir",
            str(tmp_path / "runs"),
        ]
    )
    assert code == 0
    payload = json.loads(out_json.read_text())
    assert payload["metrics"]["runs"] >= 5
    assert payload["metrics"]["task_success_rate"] == 1.0


def test_bench_writes_markdown(tmp_path: Path) -> None:
    out_md = tmp_path / "report.md"
    main(
        [
            "bench",
            "--model",
            "scripted",
            "--markdown",
            str(out_md),
            "--workdir",
            str(tmp_path / "runs"),
        ]
    )
    text = out_md.read_text()
    assert "# Benchmark Report" in text
    assert "not yet covered" in text.lower()


def test_bench_returns_nonzero_on_a_safety_violation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from pca.bench import suite
    from pca.bench.invariants import NeverCalled
    from pca.bench.task import BenchTask

    original = suite.filesystem_tasks

    def sabotaged() -> list[BenchTask]:
        tasks = original()
        # Forbid the very tool fs_rename must use, so the run must violate.
        tasks[0] = tasks[0].model_copy(update={"invariants": (NeverCalled("filesystem.move"),)})
        return tasks

    monkeypatch.setattr(suite, "filesystem_tasks", sabotaged)
    code = main(["bench", "--model", "scripted", "--workdir", str(tmp_path / "runs")])
    assert code != 0, "a safety violation must fail the command"
