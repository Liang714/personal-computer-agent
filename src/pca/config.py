"""Runtime configuration. Conservative defaults, explicit scope."""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, ConfigDict


class AgentConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    workspace_roots: list[Path]
    trash: Path
    db_path: Path
    model: str = "scripted"
    ollama_model: str = "qwen3:14b"
    auto_approve: bool = False

    @classmethod
    def default(cls) -> AgentConfig:
        home = Path.home() / "Documents" / "AI-Agent"
        return cls(
            workspace_roots=[home / "workspace"],
            trash=home / "trash",
            db_path=home / "audit.sqlite3",
        )
