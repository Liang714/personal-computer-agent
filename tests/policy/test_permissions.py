import pytest

from pca.core.errors import PolicyViolation
from pca.core.types import Capability, Permission
from pca.policy.permissions import PermissionPolicy


def test_default_is_conservative() -> None:
    policy = PermissionPolicy.default()
    assert policy.check(Capability.FILESYSTEM_READ) is Permission.ALLOWED
    assert policy.check(Capability.FILESYSTEM_WRITE) is Permission.ASK
    assert policy.check(Capability.FILESYSTEM_DELETE) is Permission.ASK


def test_unlisted_capability_defaults_to_denied() -> None:
    policy = PermissionPolicy(grants={})
    assert policy.check(Capability.FILESYSTEM_READ) is Permission.DENIED


def test_require_not_denied_raises_on_denied() -> None:
    policy = PermissionPolicy(grants={Capability.FILESYSTEM_WRITE: Permission.DENIED})
    with pytest.raises(PolicyViolation, match="filesystem_write"):
        policy.require_not_denied(Capability.FILESYSTEM_WRITE)


def test_require_not_denied_returns_setting_when_permitted() -> None:
    policy = PermissionPolicy(grants={Capability.FILESYSTEM_WRITE: Permission.ASK})
    assert policy.require_not_denied(Capability.FILESYSTEM_WRITE) is Permission.ASK
