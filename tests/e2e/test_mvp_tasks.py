"""README §43 MVP tasks, end to end on the deterministic provider."""

from pathlib import Path

import pytest

from pca.agent.machine import State
from pca.cli import build_agent
from pca.config import AgentConfig
from pca.core.types import ActionProposal


@pytest.fixture
def downloads(tmp_path: Path) -> Path:
    root = tmp_path / "work"
    root.mkdir()
    (root / "report.pdf").write_bytes(b"%PDF-1.4 report")
    (root / "invoice.pdf").write_bytes(b"%PDF-1.4 invoice")
    (root / "notes.txt").write_text("notes")
    return root


def config_for(tmp_path: Path, root: Path) -> AgentConfig:
    return AgentConfig(
        workspace_roots=[root],
        trash=tmp_path / "trash",
        db_path=tmp_path / "audit.sqlite3",
        auto_approve=True,
    )


def test_mvp_task_2_move_pdfs_into_a_new_folder(tmp_path: Path, downloads: Path) -> None:
    """'Find PDFs in Downloads and move them into a new PDF folder.'"""
    pdf_dir = downloads / "PDF"
    script = [
        [
            ActionProposal(
                intent="create the PDF folder",
                tool="filesystem.mkdir",
                arguments={"path": str(pdf_dir)},
                expected={"exists": [str(pdf_dir)]},
            )
        ],
        [
            ActionProposal(
                intent="move report.pdf",
                tool="filesystem.move",
                arguments={
                    "source": str(downloads / "report.pdf"),
                    "destination": str(pdf_dir / "report.pdf"),
                },
                expected={
                    "exists": [str(pdf_dir / "report.pdf")],
                    "absent": [str(downloads / "report.pdf")],
                },
            )
        ],
        [
            ActionProposal(
                intent="move invoice.pdf",
                tool="filesystem.move",
                arguments={
                    "source": str(downloads / "invoice.pdf"),
                    "destination": str(pdf_dir / "invoice.pdf"),
                },
                expected={
                    "exists": [str(pdf_dir / "invoice.pdf")],
                    "absent": [str(downloads / "invoice.pdf")],
                },
            )
        ],
    ]
    agent = build_agent(config_for(tmp_path, downloads), script=script)
    outcome = agent.run("move the PDFs in Downloads into a PDF folder")

    assert outcome.state is State.COMPLETE
    assert outcome.actions_taken == 3
    assert sorted(p.name for p in pdf_dir.iterdir()) == ["invoice.pdf", "report.pdf"]
    assert (downloads / "notes.txt").exists(), "non-PDF files must be untouched"


def test_mvp_task_4_rename_a_file(tmp_path: Path, downloads: Path) -> None:
    """'Find the file called report.pdf and rename it to final_report.pdf.'"""
    script = [
        [
            ActionProposal(
                intent="rename report.pdf",
                tool="filesystem.move",
                arguments={
                    "source": str(downloads / "report.pdf"),
                    "destination": str(downloads / "final_report.pdf"),
                },
                expected={
                    "exists": [str(downloads / "final_report.pdf")],
                    "absent": [str(downloads / "report.pdf")],
                },
            )
        ]
    ]
    agent = build_agent(config_for(tmp_path, downloads), script=script)
    outcome = agent.run("rename report.pdf to final_report.pdf")

    assert outcome.state is State.COMPLETE
    assert (downloads / "final_report.pdf").exists()
    assert not (downloads / "report.pdf").exists()


def test_the_whole_run_is_replayable_from_the_audit_log(tmp_path: Path, downloads: Path) -> None:
    script = [
        [
            ActionProposal(
                intent="rename report.pdf",
                tool="filesystem.move",
                arguments={
                    "source": str(downloads / "report.pdf"),
                    "destination": str(downloads / "final_report.pdf"),
                },
                expected={"exists": [str(downloads / "final_report.pdf")]},
            )
        ]
    ]
    agent = build_agent(config_for(tmp_path, downloads), script=script)
    outcome = agent.run("rename report.pdf")

    events = agent.broker.store.events(outcome.task_id)
    kinds = [e.kind.value for e in events]
    assert kinds.count("action_executed") == 1
    assert "risk_classified" in kinds
    assert "verified" in kinds
    assert all(e.seq == i + 1 for i, e in enumerate(events)), "log must be gapless"
