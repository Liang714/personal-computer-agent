"""The one place tools are assembled into a registry.

Composition roots (the CLI, the benchmark runner) call this instead of each
building their own registry. Keeping assembly in a single module means the
architecture guard in tests/test_architecture.py can stay tight: exactly one
module outside the broker may import ToolRegistry.

Nothing here executes a tool. Execution is the broker's job alone.
"""

from __future__ import annotations

from pca.tools.base import Tool
from pca.tools.filesystem.delete import delete_tools
from pca.tools.filesystem.read import read_tools
from pca.tools.filesystem.write import write_tools
from pca.tools.registry import ToolRegistry


def default_tools() -> list[Tool]:
    """Every capability the agent currently has."""
    return [*read_tools(), *write_tools(), *delete_tools()]


def build_registry() -> ToolRegistry:
    registry = ToolRegistry()
    for tool in default_tools():
        registry.register(tool)
    return registry
