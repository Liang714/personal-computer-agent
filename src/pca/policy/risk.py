"""Deterministic risk classification (spec §16, decision D3).

The model never supplies, influences, or lowers a risk level. Risk is derived
here from the resolved tool and its already-validated arguments.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from pca.core.types import Permission, RiskLevel

BULK_THRESHOLD = 10


def classify(tool_name: str, arguments: Mapping[str, Any], base: RiskLevel) -> RiskLevel:
    """Escalate the tool's declared base risk from the shape of its arguments."""
    risk = base
    if _target_count(arguments) >= BULK_THRESHOLD:
        risk = _escalate(risk)
    return risk


def requires_approval(risk: RiskLevel, permission: Permission) -> bool:
    """HIGH and above always ask, regardless of a standing ALLOWED grant."""
    if risk.rank >= RiskLevel.HIGH.rank:
        return True
    return permission is Permission.ASK


def _target_count(arguments: Mapping[str, Any]) -> int:
    total = 0
    for value in arguments.values():
        if isinstance(value, Sequence) and not isinstance(value, str | bytes):
            total += len(value)
    return total


def _escalate(risk: RiskLevel) -> RiskLevel:
    order = [RiskLevel.LOW, RiskLevel.MEDIUM, RiskLevel.HIGH, RiskLevel.CRITICAL]
    return order[min(risk.rank + 1, len(order) - 1)]
