"""Local Qwen via Ollama (decision D2).

Free, keyless, rate-limit-free and private. Parsing is deliberately strict:
a model that returns something we did not ask for is a model we stop, not a
model we interpret generously.
"""

from __future__ import annotations

import json
import re
from typing import Any

import httpx

from pca.core.types import ActionProposal
from pca.models.gateway import PlanRequest, build_prompt

_FENCE = re.compile(r"^\s*```(?:json)?\s*|\s*```\s*$", re.MULTILINE)
_ALLOWED_KEYS = {"intent", "tool", "arguments", "expected"}

# Ollama's bare format="json" constrains output to *any* valid JSON, and a
# capable model satisfies that with "{}" in two tokens. qwen3:14b did exactly
# that on every task, scoring 0% while being perfectly able to plan when asked
# unconstrained. Passing the actual schema instead keeps the structural
# guarantee without inviting the degenerate answer.
_RESPONSE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "proposals": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "intent": {"type": "string"},
                    "tool": {"type": "string"},
                    "arguments": {"type": "object"},
                    "expected": {"type": "object"},
                },
                "required": ["intent", "tool", "arguments"],
            },
        }
    },
    "required": ["proposals"],
}


def parse_proposals(raw: str) -> list[ActionProposal]:
    """Turn raw model text into validated proposals, or refuse."""
    cleaned = _FENCE.sub("", raw).strip()
    try:
        document = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise ValueError(f"could not parse model output as JSON: {exc}") from exc

    entries = document.get("proposals", [])
    proposals: list[ActionProposal] = []
    for entry in entries:
        extra = set(entry) - _ALLOWED_KEYS
        if extra:
            # A model-supplied "risk" is the §18 attack. Refuse the whole batch.
            raise ValueError(f"rejected unexpected proposal fields: {sorted(extra)}")
        proposals.append(ActionProposal.model_validate(entry))
    return proposals


class OllamaProvider:
    def __init__(
        self,
        model: str = "qwen3:14b",
        host: str = "http://localhost:11434",
        timeout: float = 120.0,
    ) -> None:
        self._model = model
        self._host = host.rstrip("/")
        self._timeout = timeout

    @property
    def model_id(self) -> str:
        return f"ollama/{self._model}"

    def propose(self, request: PlanRequest) -> list[ActionProposal]:
        response = httpx.post(
            f"{self._host}/api/generate",
            json={
                "model": self._model,
                "prompt": build_prompt(request),
                "stream": False,
                "format": _RESPONSE_SCHEMA,
                "options": {"temperature": 0.0},
            },
            timeout=self._timeout,
        )
        response.raise_for_status()
        return parse_proposals(response.json()["response"])
