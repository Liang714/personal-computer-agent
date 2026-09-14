"""Post-action verification (spec §21).

An action is not successful because it returned without raising. It is
successful because re-reading the world shows what we expected to see.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from pca.core.errors import ScopeViolation
from pca.core.types import VerificationResult
from pca.policy.paths import Workspace


def verify_filesystem(expected: Mapping[str, Any], workspace: Workspace) -> VerificationResult:
    """Check `exists` and `absent` path lists against real filesystem state."""
    must_exist = list(expected.get("exists", []))
    must_be_absent = list(expected.get("absent", []))

    if not must_exist and not must_be_absent:
        return VerificationResult(
            status="ambiguous", detail="no postcondition was stated for this action"
        )

    problems: list[str] = []
    for raw in must_exist:
        try:
            path = workspace.resolve(raw)
        except ScopeViolation:
            return VerificationResult(
                status="ambiguous",
                detail=f"expectation refers outside the workspace scope: {raw}",
            )
        if not path.exists():
            problems.append(f"expected to exist but does not: {raw}")

    for raw in must_be_absent:
        try:
            path = workspace.resolve(raw)
        except ScopeViolation:
            return VerificationResult(
                status="ambiguous",
                detail=f"expectation refers outside the workspace scope: {raw}",
            )
        if path.exists():
            problems.append(f"expected to be gone but remains: {raw}")

    if problems:
        return VerificationResult(status="failed", detail="; ".join(problems))
    return VerificationResult(status="success", detail="all postconditions hold")
