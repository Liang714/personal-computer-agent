"""Command-line entry point for the headless agent core."""

from __future__ import annotations

import argparse
import sys

from pca.agent.limits import Budget, BudgetTracker
from pca.agent.machine import Agent
from pca.broker.approval import AlwaysApprove, ApprovalUI, CliApproval
from pca.broker.broker import CapabilityBroker
from pca.composition import build_registry
from pca.config import AgentConfig
from pca.core.types import ActionProposal
from pca.models.gateway import ModelProvider
from pca.models.ollama import OllamaProvider
from pca.models.scripted import ScriptedProvider
from pca.policy.paths import Workspace
from pca.policy.permissions import PermissionPolicy
from pca.store.events import EventStore


def build_agent(config: AgentConfig, script: list[list[ActionProposal]] | None = None) -> Agent:
    for root in config.workspace_roots:
        root.mkdir(parents=True, exist_ok=True)
    config.trash.mkdir(parents=True, exist_ok=True)

    workspace = Workspace(roots=config.workspace_roots, trash=config.trash)

    approval: ApprovalUI = AlwaysApprove() if config.auto_approve else CliApproval()
    provider: ModelProvider = (
        OllamaProvider(model=config.ollama_model)
        if config.model == "ollama"
        else ScriptedProvider(script or [])
    )

    broker = CapabilityBroker(
        registry=build_registry(),
        permissions=PermissionPolicy.default(),
        workspace=workspace,
        approval=approval,
        store=EventStore(config.db_path),
        budget=BudgetTracker(Budget()),
    )
    return Agent(broker=broker, provider=provider, workspace=workspace)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="pca", description="Headless agent core")
    sub = parser.add_subparsers(dest="command", required=True)

    run_cmd = sub.add_parser("run", help="run a natural-language goal")
    run_cmd.add_argument("goal")
    run_cmd.add_argument("--model", choices=["scripted", "ollama"], default=None)

    audit_cmd = sub.add_parser("audit", help="print the audit log for a task")
    audit_cmd.add_argument("task_id")

    sub.add_parser("tools", help="list the available tool vocabulary")

    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        return int(exc.code or 2)

    config = AgentConfig.default()
    if getattr(args, "model", None):
        config = config.model_copy(update={"model": args.model})

    agent = build_agent(config)

    if args.command == "tools":
        for name in agent.broker.tool_names():
            print(name)
        return 0

    if args.command == "audit":
        for event in agent.broker.store.events(args.task_id):
            print(f"{event.ts}  {event.seq:>3}  {event.kind.value:<20} {event.payload}")
        return 0

    outcome = agent.run(args.goal)
    print(f"task {outcome.task_id}: {outcome.state.value} — {outcome.summary}")
    print(f"actions taken: {outcome.actions_taken}")
    return 0 if outcome.state.value in {"complete", "ask_user"} else 1


if __name__ == "__main__":
    sys.exit(main())
