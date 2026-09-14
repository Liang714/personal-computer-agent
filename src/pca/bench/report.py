"""Benchmark reporting: JSON for machines, Markdown for humans."""

from __future__ import annotations

import json
from collections.abc import Sequence

from pca.bench.metrics import MetricSet
from pca.bench.runner import RunRecord, Verdict
from pca.bench.task import COVERED_CATEGORIES, TaskCategory

_HEADLINE = [
    ("Task success rate", "task_success_rate", "{:.1%}"),
    ("Step success rate", "step_success_rate", "{:.1%}"),
    ("Unsafe action rate", "unsafe_action_rate", "{:.1%}"),
    ("Injection success rate", "injection_success_rate", "{:.1%}"),
    ("Policy violation rate", "policy_violation_rate", "{:.1%}"),
    ("Errored rate", "errored_rate", "{:.1%}"),
    ("Actions per task", "actions_per_task", "{:.2f}"),
    ("Model calls per task", "model_calls_per_task", "{:.2f}"),
    ("Latency p50 (ms)", "latency_p50_ms", "{:.0f}"),
    ("Latency p90 (ms)", "latency_p90_ms", "{:.0f}"),
    ("Approval burden", "approval_burden", "{:.2f}"),
]


def to_json(records: Sequence[RunRecord], metrics: MetricSet) -> str:
    return json.dumps(
        {
            "metrics": metrics.model_dump(),
            "runs": [r.model_dump(exclude={"events"}) for r in records],
        },
        indent=2,
        sort_keys=True,
    )


def to_markdown(records: Sequence[RunRecord], metrics: MetricSet) -> str:
    providers = sorted({r.provider_id for r in records})
    lines = [
        "# Benchmark Report",
        "",
        f"Runs: {metrics.runs} | Providers: {', '.join(providers) or 'none'}",
        "",
        "## Metrics",
        "",
        "| Metric | Value |",
        "|---|---|",
    ]
    lines += [
        f"| {label} | {fmt.format(getattr(metrics, field))} |" for label, field, fmt in _HEADLINE
    ]

    violations = [r for r in records if r.verdict is Verdict.SAFETY_VIOLATION]
    if violations:
        lines += ["", "## SAFETY VIOLATIONS", ""]
        lines += [f"- **{r.task_id}** - {'; '.join(r.violations)}" for r in violations]

    lines += [
        "",
        "## Runs",
        "",
        "| Task | Category | Provider | Verdict | Actions |",
        "|---|---|---|---|---|",
    ]
    lines += [
        f"| {r.task_id} | {r.category} | {r.provider_id} | {r.verdict.value} | {r.actions_taken} |"
        for r in records
    ]

    uncovered = sorted(c.value for c in TaskCategory if c not in COVERED_CATEGORIES)
    lines += [
        "",
        "## Coverage",
        "",
        f"Categories not yet covered: {', '.join(uncovered)}.",
        "",
        "These are declared in the task model but carry no tasks, because the",
        "corresponding tools do not exist yet. They are listed here rather than",
        "omitted so the report does not overstate what has been measured.",
        "",
    ]
    return "\n".join(lines)
