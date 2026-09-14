"""Command-line entry point for the headless agent core."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from pca.agent.limits import Budget, BudgetTracker
from pca.agent.machine import Agent
from pca.bench import suite
from pca.bench.metrics import compute
from pca.bench.report import to_comparison_markdown, to_json, to_markdown
from pca.bench.runner import RunRecord, Verdict, run_task
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

    bench_cmd = sub.add_parser("bench", help="run the benchmark suite")
    bench_cmd.add_argument("--model", choices=["scripted", "ollama"], default="scripted")
    bench_cmd.add_argument("--repeats", type=int, default=1)
    bench_cmd.add_argument(
        "--ollama-model",
        dest="ollama_model",
        default=None,
        help="override the Ollama model tag, e.g. qwen3:30b-a3b",
    )
    bench_cmd.add_argument("--json", dest="json_path", default=None)
    bench_cmd.add_argument("--markdown", dest="markdown_path", default=None)
    bench_cmd.add_argument("--workdir", default=None)
    bench_cmd.add_argument(
        "--baseline",
        default=None,
        help="path to an earlier --json report; renders a delta table",
    )

    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        return int(exc.code or 2)

    if args.command == "bench":
        return _run_bench(args)

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


def _ollama_reachable() -> bool:
    try:
        import httpx

        httpx.get("http://localhost:11434/api/version", timeout=2.0).raise_for_status()
    except Exception:  # noqa: BLE001 - unreachable for any reason means skip
        return False
    return True


def _run_bench(args: argparse.Namespace) -> int:
    """Run the suite. Exits non-zero on any safety violation."""
    tasks = [*suite.filesystem_tasks(), *suite.adversarial_tasks()]
    workdir = Path(args.workdir) if args.workdir else Path.cwd() / ".bench"
    control = args.model == "scripted"

    if not control and not _ollama_reachable():
        print("ollama is not reachable at localhost:11434 - skipping model runs")
        print("start it with: /Applications/Ollama.app/Contents/Resources/ollama serve")
        return 0

    ollama_model = args.ollama_model or AgentConfig.default().ollama_model
    records: list[RunRecord] = []
    for repeat in range(max(1, args.repeats)):
        for task in tasks:
            root = workdir / f"{task.id}-{repeat}"
            root.mkdir(parents=True, exist_ok=True)
            provider = None if control else OllamaProvider(model=ollama_model)
            record = run_task(task, provider, workspace_root=root, control=control, repeat=repeat)
            records.append(record)
            print(f"  {record.task_id:<28} {record.verdict.value}")

    metrics = compute(records)
    if args.json_path:
        Path(args.json_path).write_text(to_json(records, metrics), encoding="utf-8")
    if args.markdown_path:
        Path(args.markdown_path).write_text(to_markdown(records, metrics), encoding="utf-8")

    print()
    print(to_markdown(records, metrics))

    if args.baseline:
        from pca.bench.metrics import MetricSet

        baseline = MetricSet.model_validate(
            json.loads(Path(args.baseline).read_text(encoding="utf-8"))["metrics"]
        )
        print(to_comparison_markdown(baseline, metrics))

    if any(r.verdict is Verdict.SAFETY_VIOLATION for r in records):
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
