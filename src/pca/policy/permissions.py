"""Granular capability permissions (spec §15)."""

from __future__ import annotations

from collections.abc import Mapping

from pca.core.errors import PolicyViolation
from pca.core.types import Capability, Permission


class PermissionPolicy:
    """Maps a capability to DENIED / ASK / ALLOWED. Unlisted means DENIED."""

    def __init__(self, grants: Mapping[Capability, Permission] | None = None) -> None:
        self._grants: dict[Capability, Permission] = dict(grants or {})

    @classmethod
    def default(cls) -> PermissionPolicy:
        return cls(
            {
                Capability.FILESYSTEM_READ: Permission.ALLOWED,
                Capability.FILESYSTEM_WRITE: Permission.ASK,
                Capability.FILESYSTEM_DELETE: Permission.ASK,
            }
        )

    def check(self, capability: Capability) -> Permission:
        return self._grants.get(capability, Permission.DENIED)

    def require_not_denied(self, capability: Capability) -> Permission:
        setting = self.check(capability)
        if setting is Permission.DENIED:
            raise PolicyViolation(f"capability denied: {capability.value}")
        return setting
