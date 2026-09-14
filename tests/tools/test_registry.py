import pytest
from pydantic import BaseModel, ConfigDict

from pca.core.errors import SchemaRejected
from pca.core.types import ActionProposal, Capability, RiskLevel, ToolResult
from pca.policy.paths import Workspace
from pca.tools.base import Tool
from pca.tools.registry import ToolRegistry


class EchoIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    message: str


class EchoOut(BaseModel):
    model_config = ConfigDict(extra="forbid")
    message: str


class EchoTool(Tool):
    name = "test.echo"
    version = "1"
    capability = Capability.FILESYSTEM_READ
    base_risk = RiskLevel.LOW
    Input = EchoIn
    Output = EchoOut

    def run(self, args: BaseModel, workspace: Workspace) -> ToolResult:
        assert isinstance(args, EchoIn)
        return ToolResult(ok=True, data={"message": args.message})


@pytest.fixture
def registry() -> ToolRegistry:
    r = ToolRegistry()
    r.register(EchoTool())
    return r


def test_resolves_a_known_tool(registry: ToolRegistry) -> None:
    proposal = ActionProposal(intent="i", tool="test.echo", arguments={"message": "hi"})
    tool, args = registry.resolve(proposal)
    assert tool.name == "test.echo"
    assert isinstance(args, EchoIn)
    assert args.message == "hi"


def test_rejects_unknown_tool(registry: ToolRegistry) -> None:
    proposal = ActionProposal(intent="i", tool="filesystem.nuke", arguments={})
    with pytest.raises(SchemaRejected, match="unknown tool"):
        registry.resolve(proposal)


def test_rejects_unknown_argument(registry: ToolRegistry) -> None:
    proposal = ActionProposal(
        intent="i", tool="test.echo", arguments={"message": "hi", "sudo": True}
    )
    with pytest.raises(SchemaRejected, match="invalid arguments"):
        registry.resolve(proposal)


def test_rejects_missing_argument(registry: ToolRegistry) -> None:
    proposal = ActionProposal(intent="i", tool="test.echo", arguments={})
    with pytest.raises(SchemaRejected, match="invalid arguments"):
        registry.resolve(proposal)


def test_duplicate_registration_is_an_error(registry: ToolRegistry) -> None:
    with pytest.raises(ValueError, match="already registered"):
        registry.register(EchoTool())
