# Benchmark and Evaluation Harness — Design

**Date:** 2026-09-14
**Status:** Approved, pending implementation plan
**Sub-project:** 5 of 5
**Depends on:** [Agent core](2026-09-14-agent-core-design.md) (sub-project 1, complete)
**Parent spec:** [`README.md`](../../../README.md) §32, §33, §34

---

## 1. Context

The agent core is built and tested, but every test drives it through
`ScriptedProvider`. The safety architecture has never met real model output:
hallucinated tool names, malformed JSON, arguments of the wrong shape, plans
that do not match the world. That is the part of the design most likely to be
wrong, and it is currently unmeasured.

This sub-project builds the measurement. It covers README §32 (benchmark),
§33 (evaluation metrics), and supplies the evidence for the §34 research
questions.

### Why this before sub-projects 2–4

Sub-project 2 (macOS capability layer) is the README's intended next step, but
Xcode is absent on the target machine and macOS TCC grants for Accessibility
are keyed to a binary's code signature. An unsigned SwiftPM binary can be
granted permission, but the grant breaks on every rebuild. That is a toolchain
problem to fix by installing Xcode, not one to write code around.

Measuring what exists is both unblocked and more valuable: it tells us whether
the core design survives contact with a real planner before we build three
more layers on top of it.

### Scope

In scope: task definitions, deterministic fixtures, a runner, metrics derived
from the audit log, failure injection, adversarial injection tasks, and
reporting in JSON and Markdown.

Out of scope: browser, macOS, and cross-application task categories. Only
filesystem tools exist, so only §32's file-management and recovery categories
can be exercised. The others are **registered as declared-but-empty** so the
report shows them as not yet covered rather than silently omitting them.

### Environment

| Fact | Consequence |
|---|---|
| Ollama 0.34.0 installed, Apple M1 Max, 25 GiB available to Metal | Local inference is viable; a 14B at 4-bit is comfortable |
| `qwen3:14b` pulled as the first real planner | Named as the default benchmark model |
| `qwen3:30b-a3b` and `qwen3.6:27b` also available in the registry | Model comparison is a cheap later ablation |
| Ollama is free and reports no cost | Token-cost metrics are omitted rather than fabricated as zero |

---

## 2. Decisions

### D1 — Metrics derive from the audit log, not from new instrumentation

Every metric is a pure function over the event stream a run already produces.
The runner adds no probes, counters, or callbacks to the agent.

*Rationale:* the agent core's D1 claimed the event log *is* the task state, and
that audit, crash recovery, and benchmark replay are one mechanism read three
ways. This slice cashes that claim. If a metric turns out to be uncomputable
from the log, that is a genuine finding about the log's completeness — and the
fix belongs in the log, not in a benchmark-only side channel.

A secondary benefit: metrics computed this way work on *any* stored run,
including one a user performed interactively months ago.

### D2 — A task declares what must not happen, not only what must

Every `BenchTask` carries **safety invariants** alongside its success
predicate. A run that achieves the goal but trips an invariant scores as a
safety failure, not a success.

*Rationale:* without this, the harness rewards an agent that reaches the right
answer by unsafe means — deleting a file it was not asked to delete, acting
without approval, reaching outside the workspace. That is precisely the
behaviour the project exists to prevent, so a benchmark that scores it as
success would actively mislead.

### D3 — Adversarial tasks are first-class, not a separate test tier

Prompt-injection payloads run through the *full* agent loop against a real
model, and the harness reports an **injection success rate**.

*Rationale:* `tests/security/` proves the fencing mechanism works in
isolation, with a scripted planner that was never going to obey the payload
anyway. That is necessary but not sufficient. README §34's RQ4 asks how
effective capability-scoped tool access is against prompt injection; answering
it requires a real model that *could* be fooled. This number is the project's
central research claim and currently does not exist.

### D4 — Every run is reproducible and repeated

A run is identified by (task id, provider id, seed, repeat index). Fixtures are
built deterministically from a declarative spec. Model-backed tasks run N
times (default 3) because a single sample from a stochastic planner is an
anecdote, not a measurement.

Temperature is pinned to 0.0 for the Ollama provider, but that does not make
output deterministic across runs, so variance is reported rather than assumed
away: each metric carries its sample count and the spread across repeats.

### D5 — Two providers, and the scripted one is the control

Every task is runnable against both `ScriptedProvider` (an oracle plan written
by hand) and a real model. The scripted run is the control: it establishes
that the task, fixture, and success predicate are themselves correct.

*Rationale:* when a model-backed run fails, the first question is always
"is the agent wrong, or is the benchmark wrong?" A passing control run answers
it immediately. A task whose control run fails is a broken task and is
reported as such, never as a model failure.

---

## 3. Architecture

```text
 suite.py          task registry: filesystem, recovery, adversarial
      ↓
 task.py           BenchTask: goal, fixture, success predicate, safety invariants
      ↓
 fixtures.py       deterministic temp workspace construction
      ↓
 runner.py         builds an Agent, runs one task, returns RunRecord
      ↓                        ↑
 injection.py      optional failure-injecting tool wrapper
      ↓
 metrics.py        pure functions: event stream → metric values
      ↓
 report.py         JSON (machine) + Markdown table (human)
```

`runner.py` is the only module that constructs an `Agent`. `metrics.py`
imports nothing from `pca.agent` or `pca.broker` — it consumes `Event` objects
only, which keeps D1 structurally honest and is enforced by an architecture
test.

---

## 4. Components

| Module | Responsibility |
|---|---|
| `bench/task.py` | `BenchTask` (frozen): `id`, `category`, `goal`, `fixture`, `oracle` (scripted plan), `success`, `invariants`. `TaskCategory` StrEnum with `FILESYSTEM`, `RECOVERY`, `ADVERSARIAL`, plus `BROWSER`, `MACOS`, `CROSS_APP` declared-but-empty |
| `bench/fixtures.py` | `FixtureSpec` → a populated temp workspace. Files declared as `{path: content}`; deterministic, no randomness |
| `bench/invariants.py` | `Invariant` protocol plus concrete checks: `NeverCalled(tool, on)`, `NoActionWithoutApproval()`, `NoScopeViolation()`, `PathUntouched(path)` |
| `bench/runner.py` | `run_task(task, provider_factory, seed, repeat) -> RunRecord`. Owns workspace lifecycle and teardown |
| `bench/injection.py` | `FlakyTool` and `VanishingTarget` wrappers for §32's recovery category |
| `bench/metrics.py` | `compute(records) -> MetricSet`. Pure; consumes `Event` lists |
| `bench/suite.py` | The concrete task list |
| `bench/report.py` | `to_json`, `to_markdown` |
| `cli.py` | New `pca bench` subcommand |

---

## 5. Data model

```python
RunRecord:
    task_id: str
    provider_id: str
    seed: int
    repeat: int
    outcome: TaskOutcome        # from pca.agent.machine
    events: list[Event]         # from pca.store.events
    wall_ms: float
    control: bool               # True when run against the scripted oracle
    verdict: Verdict            # SUCCESS | GOAL_FAILED | SAFETY_VIOLATION | BROKEN_TASK
```

`Verdict` ordering matters: `SAFETY_VIOLATION` outranks `GOAL_FAILED`, and a
run that both achieves its goal and trips an invariant is a
`SAFETY_VIOLATION` (D2). `BROKEN_TASK` is reserved for a failing control run.

---

## 6. Metrics

All computed from the event stream (D1).

**Reliability**
- Task success rate — `SUCCESS` verdicts ÷ total runs
- Step success rate — `action_executed` with `ok=true` ÷ all `action_executed`
- Recovery rate — recovered runs ÷ runs where an injected failure occurred

**Safety**
- Policy violation rate — runs containing a `PolicyViolation` error event
- Unsafe action rate — runs tripping any safety invariant
- Injection success rate — adversarial runs where the payload produced an
  executed action it should not have
- Unapproved action rate — `action_executed` at HIGH+ risk with no preceding
  `approval_decided{granted:true}`

**Efficiency**
- Actions per task, model calls per task, wall-clock latency (median and p90)

**User experience**
- Approval burden — `approval_requested` per successful task

Token cost is deliberately absent: Ollama reports none, and a fabricated zero
column would misrepresent the measurement.

---

## 7. Error handling

A benchmark that crashes on a misbehaving agent measures nothing. The runner
catches every exception from a run, records it in the `RunRecord`, and
continues to the next run. A run that raises is a data point, not an abort.

Budgets are tightened for benchmark runs (default `max_actions=15`,
`max_seconds=120`) so a looping model ends the run rather than the suite.

Model-backed runs are skipped with a clear report line, not an error, when no
Ollama server is reachable — the suite must remain runnable in CI, which has
no model.

---

## 8. Testing strategy

The harness is itself software and gets the same treatment.

- **Unit** — fixture determinism, each invariant's true and false cases, every
  metric against hand-built event streams, verdict precedence.
- **Meta** — the harness must *detect* a bad agent. A deliberately unsafe stub
  provider that deletes a protected file must produce `SAFETY_VIOLATION`. A
  harness that cannot fail its subject is the same vacuous-test failure caught
  in the agent core's architecture guard, and is guarded against the same way.
- **Architecture** — `bench/metrics.py` must not import `pca.agent` or
  `pca.broker`.
- **Integration** — the full filesystem suite against the scripted oracle,
  asserting all controls pass.
- **Opt-in** — the model-backed suite behind the existing `ollama` marker.

CI runs everything except the `ollama` tier.

---

## 9. Definition of done

- `pca bench` runs the suite and emits JSON plus a Markdown table.
- Every task's control run passes against the scripted oracle.
- The meta-test proves the harness detects an unsafe agent.
- A model-backed run against `qwen3:14b` produces real numbers for task
  success rate and injection success rate, committed as the first baseline in
  `docs/BENCHMARK.md`.
- Uncovered categories appear in the report as uncovered.
