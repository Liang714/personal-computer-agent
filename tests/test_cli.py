from pathlib import Path

import pytest

from pca.cli import main
from pca.config import AgentConfig


@pytest.fixture
def config(tmp_path: Path) -> AgentConfig:
    root = tmp_path / "work"
    root.mkdir()
    (root / "a.txt").write_text("alpha")
    return AgentConfig(
        workspace_roots=[root],
        trash=tmp_path / "trash",
        db_path=tmp_path / "audit.sqlite3",
    )


def test_tools_command_lists_the_vocabulary(
    config: AgentConfig,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(AgentConfig, "default", classmethod(lambda cls: config))
    assert main(["tools"]) == 0
    out = capsys.readouterr().out
    assert "filesystem.list" in out
    assert "filesystem.delete" in out


def test_run_with_no_model_configured_completes_without_acting(
    config: AgentConfig,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(AgentConfig, "default", classmethod(lambda cls: config))
    assert main(["run", "do nothing"]) == 0
    assert "complete" in capsys.readouterr().out.lower()


def test_audit_prints_the_event_log(
    config: AgentConfig,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(AgentConfig, "default", classmethod(lambda cls: config))
    main(["run", "do nothing"])
    task_id = capsys.readouterr().out.split("task ")[1].split(":")[0]
    assert main(["audit", task_id]) == 0
    assert "task_started" in capsys.readouterr().out


def test_unknown_command_returns_nonzero() -> None:
    assert main(["nonsense"]) != 0
