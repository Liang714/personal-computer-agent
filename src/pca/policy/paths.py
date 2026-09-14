"""Capability-scoped filesystem boundary (spec §13)."""

from __future__ import annotations

import unicodedata
from collections.abc import Sequence
from pathlib import Path

from pca.core.errors import ScopeViolation


class Workspace:
    """The only place paths become real. Everything outside the roots is denied."""

    def __init__(self, roots: Sequence[Path], trash: Path) -> None:
        if not roots:
            raise ValueError("a workspace needs at least one root")
        self._roots = [r.expanduser().resolve() for r in roots]
        self._trash = trash.expanduser().resolve()

    @property
    def roots(self) -> list[Path]:
        return list(self._roots)

    @property
    def trash(self) -> Path:
        return self._trash

    def resolve(self, raw: str) -> Path:
        """Normalise, expand, resolve symlinks, then enforce containment."""
        normalised = unicodedata.normalize("NFKC", raw)
        if normalised != raw and any(part in normalised for part in ("../", "..\\")):
            raise ScopeViolation(f"path uses confusable characters: {raw!r}")

        candidate = Path(normalised).expanduser()
        if not candidate.is_absolute():
            # Relative paths are workspace-relative, not CWD-relative. Resolving
            # against the process CWD made every natural "data.csv" escape the
            # workspace and get refused -- a real model run produced exactly
            # that in 6 of 15 tasks. Anchoring here is also strictly safer:
            # traversal is still caught by the containment check below.
            candidate = self._roots[0] / candidate
        resolved = candidate.resolve()

        if not self.contains(resolved):
            raise ScopeViolation(f"path escapes workspace: {raw!r} resolved to {resolved}")
        return resolved

    def contains(self, path: Path) -> bool:
        resolved = path.resolve()
        for root in (*self._roots, self._trash):
            if resolved == root or root in resolved.parents:
                return True
        return False
